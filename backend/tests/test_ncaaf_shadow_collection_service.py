from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.database.base import Base
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.ncaaf_power_market_shadow_record import NcaafPowerMarketShadowRecord
from app.models.ncaaf_power_market_shadow_result import NcaafPowerMarketShadowResult
from app.models.odds import Odds
from app.models.prediction_power_snapshot import PredictionPowerSnapshot
from app.models.team import Team
from app.models.team_power_rating import TeamPowerRatingRecord
from app.services import ncaaf_shadow_collection_service as collection
from app.services.ncaaf_power_market_shadow_service import PROSPECTIVE_FROZEN


NOW = datetime(2026, 9, 6, 16, tzinfo=UTC)


@pytest.fixture()
def session_factory(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(settings, "NCAAF_SHADOW_COLLECTION_ENABLED", True)
    monkeypatch.setattr(
        settings,
        "NCAAF_SHADOW_SPEC_VERSION",
        "NCAAF-SHADOW-1.0",
    )
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)


def _seed_candidate(session_factory, *, kickoff=NOW - timedelta(hours=1)):
    db = session_factory()
    home = Team(name="Collection Home", sport="NCAAF", league="NCAAF")
    away = Team(name="Collection Away", sport="NCAAF", league="NCAAF")
    db.add_all((home, away))
    db.flush()
    history_kickoff = kickoff - timedelta(days=7)
    history = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2026,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=history_kickoff.replace(tzinfo=None),
        status="final",
        neutral_site=True,
        home_score=28,
        away_score=14,
    )
    target = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2026,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=kickoff.replace(tzinfo=None),
        status="scheduled",
        neutral_site=False,
    )
    db.add_all((history, target))
    db.flush()
    db.add(
        GameResultObservation(
            game_id=history.id,
            provider="cfbd",
            status="final",
            home_score=28,
            away_score=14,
            observed_at=(history_kickoff + timedelta(hours=4)).replace(tzinfo=None),
        )
    )
    db.add(
        Odds(
            game_id=target.id,
            sportsbook="Collection Book",
            spread_home=-7.0,
            spread_away=7.0,
            created_at=(kickoff - timedelta(hours=1)).replace(tzinfo=None),
        )
    )
    prior_as_of = datetime(2026, 1, 15, tzinfo=UTC)
    for team, rating in ((home, 5.0), (away, -5.0)):
        db.add(
            TeamPowerRatingRecord(
                sport="NCAAF",
                season=2025,
                team_id=team.id,
                model_version="NCAAF-POWER-1.0",
                rating=rating,
                uncertainty=1.0,
                games_used=12,
                effective_games=10.0,
                rating_as_of=prior_as_of,
                source_max_observed_at=prior_as_of,
                training_game_count=100,
                input_hash="a" * 64,
            )
        )
    db.commit()
    target_id = target.id
    db.close()
    return target_id


def _frozen_values(record):
    return {
        column.name: getattr(record, column.name)
        for column in NcaafPowerMarketShadowRecord.__table__.columns
        if column.name not in {"id", "created_at"}
    }


def test_disabled_mode_opens_no_session_and_makes_no_calls(monkeypatch):
    monkeypatch.setattr(settings, "NCAAF_SHADOW_COLLECTION_ENABLED", False)
    session_factory = MagicMock(side_effect=AssertionError("session opened"))
    create = MagicMock(side_effect=AssertionError("generation called"))
    evaluate = MagicMock(side_effect=AssertionError("evaluation called"))
    monkeypatch.setattr(collection, "create_shadow_record_for_game", create)
    monkeypatch.setattr(collection, "evaluate_shadow_record", evaluate)

    generated = collection.collect_ncaaf_shadow_evidence(
        generated_at=NOW,
        session_factory=session_factory,
    )
    settled = collection.settle_ncaaf_shadow_evidence(
        settled_at=NOW,
        session_factory=session_factory,
    )

    assert generated.shadow_enabled is False
    assert settled.shadow_enabled is False
    session_factory.assert_not_called()
    create.assert_not_called()
    evaluate.assert_not_called()


def test_enabled_generation_is_prospective_idempotent_and_bounded(session_factory):
    target_id = _seed_candidate(session_factory)

    first = collection.collect_ncaaf_shadow_evidence(
        generated_at=NOW,
        session_factory=session_factory,
    )
    second = collection.collect_ncaaf_shadow_evidence(
        generated_at=NOW + timedelta(minutes=5),
        session_factory=session_factory,
    )

    db = session_factory()
    record = db.query(NcaafPowerMarketShadowRecord).one()
    assert first.eligible_candidates == 1
    assert first.created == 1
    assert second.eligible_candidates == 0
    assert record.game_id == target_id
    assert record.generation_provenance == PROSPECTIVE_FROZEN
    assert db.query(NcaafPowerMarketShadowRecord).count() == 1
    assert db.query(TeamPowerRatingRecord).count() == 2
    assert db.query(PredictionPowerSnapshot).count() == 0
    db.close()


def test_late_generation_is_marked_missed_without_record(session_factory):
    target_id = _seed_candidate(session_factory)
    db = session_factory()
    db.add(
        GameResultObservation(
            game_id=target_id,
            provider="cfbd",
            status="final",
            home_score=24,
            away_score=21,
            observed_at=(NOW - timedelta(minutes=10)).replace(tzinfo=None),
        )
    )
    db.commit()
    db.close()

    summary = collection.collect_ncaaf_shadow_evidence(
        generated_at=NOW,
        session_factory=session_factory,
    )

    db = session_factory()
    assert summary.missed_prospective_window == 1
    assert summary.created == 0
    assert db.get(Game, target_id).status == "scheduled"
    assert db.query(NcaafPowerMarketShadowRecord).count() == 0
    db.close()


def test_settlement_is_separate_immutable_and_idempotent(session_factory):
    target_id = _seed_candidate(session_factory)
    collection.collect_ncaaf_shadow_evidence(
        generated_at=NOW,
        session_factory=session_factory,
    )
    db = session_factory()
    record = db.query(NcaafPowerMarketShadowRecord).one()
    frozen = _frozen_values(record)
    target = db.get(Game, target_id)
    target.status = "final"
    target.home_score = 24
    target.away_score = 21
    target.completed_at = (NOW + timedelta(minutes=20)).replace(tzinfo=None)
    db.commit()
    db.close()

    first = collection.settle_ncaaf_shadow_evidence(
        settled_at=NOW + timedelta(minutes=30),
        session_factory=session_factory,
    )
    second = collection.settle_ncaaf_shadow_evidence(
        settled_at=NOW + timedelta(minutes=35),
        session_factory=session_factory,
    )

    db = session_factory()
    assert first.eligible_existing_records == 1
    assert first.evaluated == 1
    assert second.eligible_existing_records == 0
    assert db.query(NcaafPowerMarketShadowResult).count() == 1
    assert _frozen_values(db.query(NcaafPowerMarketShadowRecord).one()) == frozen
    db.close()


def test_generation_failure_rolls_back_only_shadow_transaction(
    session_factory,
    monkeypatch,
):
    target_id = _seed_candidate(session_factory)
    monkeypatch.setattr(
        collection,
        "create_shadow_record_for_game",
        MagicMock(side_effect=RuntimeError("shadow failed")),
    )

    summary = collection.collect_ncaaf_shadow_evidence(
        generated_at=NOW,
        session_factory=session_factory,
    )

    db = session_factory()
    assert summary.errors == 1
    assert db.get(Game, target_id) is not None
    assert db.query(Odds).filter(Odds.game_id == target_id).count() == 1
    assert db.query(NcaafPowerMarketShadowRecord).count() == 0
    db.close()


def test_settlement_failure_preserves_final_result(session_factory, monkeypatch):
    target_id = _seed_candidate(session_factory)
    collection.collect_ncaaf_shadow_evidence(
        generated_at=NOW,
        session_factory=session_factory,
    )
    db = session_factory()
    target = db.get(Game, target_id)
    target.status = "final"
    target.home_score = 31
    target.away_score = 20
    target.completed_at = (NOW + timedelta(minutes=10)).replace(tzinfo=None)
    db.commit()
    db.close()
    monkeypatch.setattr(
        collection,
        "evaluate_shadow_record",
        MagicMock(side_effect=RuntimeError("evaluation failed")),
    )

    summary = collection.settle_ncaaf_shadow_evidence(
        settled_at=NOW + timedelta(minutes=20),
        session_factory=session_factory,
    )

    db = session_factory()
    target = db.get(Game, target_id)
    assert summary.errors == 1
    assert (target.status, target.home_score, target.away_score) == ("final", 31, 20)
    assert db.query(NcaafPowerMarketShadowResult).count() == 0
    db.close()


def test_generation_horizon_excludes_games_older_than_24_hours(session_factory):
    _seed_candidate(session_factory, kickoff=NOW - timedelta(hours=24, seconds=1))

    summary = collection.collect_ncaaf_shadow_evidence(
        generated_at=NOW,
        session_factory=session_factory,
    )

    db = session_factory()
    assert summary.eligible_candidates == 0
    assert db.query(NcaafPowerMarketShadowRecord).count() == 0
    db.close()