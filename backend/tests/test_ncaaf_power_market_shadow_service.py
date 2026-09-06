from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.ncaaf_power_market_shadow import PRICE_SOURCE
from app.database.base import Base
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.ncaaf_power_market_shadow_record import (
    NcaafPowerMarketShadowRecord,
)
from app.models.ncaaf_power_market_shadow_result import (
    NcaafPowerMarketShadowResult,
)
from app.models.nik_score import NikScore
from app.models.npi_factor_result import NPIFactorResult
from app.models.odds import Odds
from app.models.prediction_power_snapshot import PredictionPowerSnapshot
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.team_power_rating import TeamPowerRatingRecord
from app.services.ncaaf_power_market_shadow_service import (
    BEFORE_KICKOFF,
    CREATED,
    INSUFFICIENT_HISTORY,
    NO_PREGAME_MARKET,
    PROSPECTIVE_FROZEN,
    RETROSPECTIVE_ASOF,
    REUSED,
    SHADOW_SPEC_VERSION,
    UNKNOWN_NEUTRAL,
    ShadowEvidenceIntegrityError,
    build_frozen_evidence_report,
    create_shadow_record_for_game,
    evaluate_shadow_record,
)
from app.services.ncaaf_power_rating_service import MODEL_VERSION
from app.services.ncaaf_power_snapshot_service import calculate_pregame_power_snapshot


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _team(db, name):
    team = Team(name=name, sport="NCAAF", league="NCAAF")
    db.add(team)
    db.flush()
    return team


def _game(
    db,
    home,
    away,
    kickoff,
    *,
    status="scheduled",
    neutral=False,
    scores=None,
):
    game = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2026,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=kickoff.replace(tzinfo=None),
        status=status,
        neutral_site=neutral,
        home_score=scores[0] if scores else None,
        away_score=scores[1] if scores else None,
    )
    db.add(game)
    db.flush()
    return game


def _observation(db, game, observed_at, scores):
    observation = GameResultObservation(
        game_id=game.id,
        provider="cfbd",
        status="final",
        home_score=scores[0],
        away_score=scores[1],
        observed_at=observed_at.replace(tzinfo=None),
    )
    db.add(observation)
    db.flush()
    return observation


def _odds(db, game, created_at, spread_home=-7.0):
    odds = Odds(
        game_id=game.id,
        sportsbook="Frozen Book",
        spread_home=spread_home,
        spread_away=-spread_home,
        created_at=created_at.replace(tzinfo=None),
    )
    db.add(odds)
    db.flush()
    return odds


def _scenario(db, *, target_status="scheduled"):
    home = _team(db, "Evidence Home")
    away = _team(db, "Evidence Away")
    third = _team(db, "Evidence Third")
    start = datetime(2026, 8, 20, 16, tzinfo=UTC)
    history = _game(
        db,
        home,
        away,
        start,
        status="final",
        neutral=True,
        scores=(28, 14),
    )
    _observation(db, history, start + timedelta(hours=6), (28, 14))
    kickoff = start + timedelta(days=7)
    target_scores = (24, 21) if target_status == "final" else None
    target = _game(
        db,
        home,
        away,
        kickoff,
        status=target_status,
        scores=target_scores,
    )
    market = _odds(db, target, kickoff - timedelta(hours=1))
    prior = {home.id: 5.0, away.id: -5.0, third.id: 0.0}
    return home, away, third, target, market, prior, kickoff


def _frozen_values(record):
    return {
        column.name: getattr(record, column.name)
        for column in NcaafPowerMarketShadowRecord.__table__.columns
        if column.name not in {"id", "created_at"}
    }


def test_empty_evidence_report_is_ready_for_cold_start(db):
    report = build_frozen_evidence_report(db)

    assert report["provenance"][PROSPECTIVE_FROZEN]["record_count"] == 0
    assert report["provenance"][RETROSPECTIVE_ASOF]["settled_count"] == 0
    assert report["readiness_checkpoints"]["25"] == {
        "status": "PENDING",
        "remaining": 25,
    }


def test_generation_is_versioned_idempotent_and_price_labeled(db):
    _, _, _, target, market, prior, kickoff = _scenario(db)
    generated_at = kickoff + timedelta(minutes=1)

    first = create_shadow_record_for_game(
        db,
        target.id,
        generated_at=generated_at,
        prior_ratings=prior,
    )
    second = create_shadow_record_for_game(
        db,
        target.id,
        generated_at=generated_at + timedelta(minutes=1),
        prior_ratings=prior,
    )

    assert first.state == CREATED
    assert second.state == REUSED
    assert first.record.id == second.record.id
    assert db.query(NcaafPowerMarketShadowRecord).count() == 1
    assert first.record.power_model_version == MODEL_VERSION
    assert first.record.shadow_spec_version == SHADOW_SPEC_VERSION
    assert first.record.generation_provenance == PROSPECTIVE_FROZEN
    assert first.record.odds_snapshot_id == market.id
    assert first.record.spread_price == -110
    assert first.record.price_source == PRICE_SOURCE
    assert 0.25 <= first.record.p_home_cover_shadow <= 0.75
    assert db.query(TeamPowerRatingRecord).count() == 0
    assert db.query(PredictionPowerSnapshot).count() == 0


def test_conflicting_backfilled_pregame_market_raises(db):
    _, _, _, target, _, prior, kickoff = _scenario(db)
    created = create_shadow_record_for_game(
        db,
        target.id,
        generated_at=kickoff + timedelta(minutes=1),
        prior_ratings=prior,
    )
    _odds(db, target, kickoff - timedelta(minutes=30), spread_home=-20.0)

    with pytest.raises(ShadowEvidenceIntegrityError, match="odds_snapshot_id"):
        create_shadow_record_for_game(
            db,
            target.id,
            generated_at=kickoff + timedelta(hours=1),
            prior_ratings=prior,
        )

    assert db.query(NcaafPowerMarketShadowRecord).one().id == created.record.id


def test_frozen_record_survives_external_rows_and_settlement(db):
    home, away, third, target, _, prior, kickoff = _scenario(db)
    generated = create_shadow_record_for_game(
        db,
        target.id,
        generated_at=kickoff + timedelta(minutes=1),
        prior_ratings=prior,
    )
    frozen = _frozen_values(generated.record)
    _odds(db, target, kickoff + timedelta(minutes=1), spread_home=-40.0)
    future = _game(
        db,
        home,
        third,
        kickoff + timedelta(days=7),
        status="final",
        neutral=True,
        scores=(70, 0),
    )
    _observation(db, future, kickoff + timedelta(days=7, hours=3), (70, 0))
    target.status = "final"
    target.home_score = 24
    target.away_score = 21
    target.completed_at = (kickoff + timedelta(hours=3)).replace(tzinfo=None)
    _observation(db, target, kickoff + timedelta(hours=3), (24, 21))
    prediction = Prediction(
        game_id=target.id,
        model_version="NPI-4.0",
        market="spread",
        selection="AWAY",
        npi_score=-999,
    )
    db.add(prediction)
    db.flush()
    db.add_all(
        (
            PredictionResult(
                prediction_id=prediction.id,
                actual_result="HOME",
                predicted_result="AWAY",
                outcome="LOSS",
            ),
            NikScore(game_id=target.id, final_npi=-999, model_version="NPI-4.0"),
            NPIFactorResult(
                prediction_id=prediction.id,
                factor_name="market",
                weight=999,
                factor_score=-999,
            ),
        )
    )
    db.flush()

    repeated = create_shadow_record_for_game(
        db,
        target.id,
        generated_at=kickoff + timedelta(hours=4),
        prior_ratings=prior,
    )
    evaluated = evaluate_shadow_record(
        db,
        generated.record.id,
        settled_at=kickoff + timedelta(hours=4),
    )

    assert repeated.state == REUSED
    assert _frozen_values(repeated.record) == frozen
    assert evaluated.state == CREATED
    assert evaluated.result.actual_home_margin == 3
    assert evaluated.result.model_margin_error == pytest.approx(
        3 - generated.record.independent_model_margin
    )
    assert evaluated.result.market_margin_error == pytest.approx(
        3 - generated.record.market_margin
    )
    assert _frozen_values(generated.record) == frozen


def test_result_conflict_does_not_mutate_frozen_record(db):
    _, _, _, target, _, prior, kickoff = _scenario(db)
    generated = create_shadow_record_for_game(
        db,
        target.id,
        generated_at=kickoff + timedelta(minutes=1),
        prior_ratings=prior,
    )
    frozen = _frozen_values(generated.record)
    target.status = "final"
    target.home_score = 24
    target.away_score = 21
    first = evaluate_shadow_record(db, generated.record.id, settled_at=kickoff + timedelta(hours=3))
    target.home_score = 10
    target.away_score = 30

    with pytest.raises(ShadowEvidenceIntegrityError, match="home_score"):
        evaluate_shadow_record(db, generated.record.id, settled_at=kickoff + timedelta(hours=4))

    assert db.query(NcaafPowerMarketShadowResult).one().id == first.result.id
    assert _frozen_values(generated.record) == frozen


def test_target_result_never_enters_frozen_power_inputs(db):
    _, _, _, target, _, prior, kickoff = _scenario(db)
    generated = create_shadow_record_for_game(
        db,
        target.id,
        generated_at=kickoff + timedelta(minutes=1),
        prior_ratings=prior,
    )
    target.status = "final"
    target.home_score = 100
    target.away_score = 0
    _observation(db, target, kickoff + timedelta(hours=3), (100, 0))

    recalculated = calculate_pregame_power_snapshot(
        db,
        target.id,
        rating_as_of=kickoff,
        prior_ratings=prior,
    )

    assert target.id not in {
        game.game_id for game in recalculated.rating_calculation.eligible_games
    }
    assert recalculated.rating_input_hash == generated.record.power_input_hash
    assert recalculated.independent_model_margin == pytest.approx(
        generated.record.independent_model_margin
    )


def test_eligibility_reasons_are_explicit(db):
    home, away, _, target, _, prior, kickoff = _scenario(db)
    early = create_shadow_record_for_game(
        db,
        target.id,
        generated_at=kickoff - timedelta(seconds=1),
        prior_ratings=prior,
    )
    unknown = _game(db, home, away, kickoff, neutral=None)
    _odds(db, unknown, kickoff - timedelta(hours=1))
    no_market = _game(db, home, away, kickoff, neutral=False)
    cold_home = _team(db, "Cold Home")
    cold_away = _team(db, "Cold Away")
    cold = _game(db, cold_home, cold_away, kickoff, neutral=False)
    _odds(db, cold, kickoff - timedelta(hours=1))

    assert early.state == BEFORE_KICKOFF
    assert create_shadow_record_for_game(
        db, unknown.id, generated_at=kickoff, prior_ratings=prior
    ).state == UNKNOWN_NEUTRAL
    assert create_shadow_record_for_game(
        db, no_market.id, generated_at=kickoff, prior_ratings=prior
    ).state == NO_PREGAME_MARKET
    assert create_shadow_record_for_game(
        db, cold.id, generated_at=kickoff, prior_ratings=prior
    ).state == INSUFFICIENT_HISTORY


def test_evidence_report_separates_provenance_and_checkpoints(db):
    home, away, _, target, _, prior, kickoff = _scenario(db)
    prospective = create_shadow_record_for_game(
        db,
        target.id,
        generated_at=kickoff + timedelta(minutes=1),
        prior_ratings=prior,
    )
    target.status = "final"
    target.home_score = 24
    target.away_score = 21
    evaluate_shadow_record(db, prospective.record.id, settled_at=kickoff + timedelta(hours=3))
    retrospective_target = _game(
        db,
        home,
        away,
        kickoff + timedelta(days=7),
        status="final",
        scores=(17, 14),
    )
    retrospective_target.completed_at = retrospective_target.game_date + timedelta(hours=3)
    _odds(db, retrospective_target, retrospective_target.game_date.replace(tzinfo=UTC) - timedelta(hours=1))
    retrospective = create_shadow_record_for_game(
        db,
        retrospective_target.id,
        generated_at=retrospective_target.game_date.replace(tzinfo=UTC) + timedelta(hours=3),
        prior_ratings=prior,
    )
    evaluate_shadow_record(
        db,
        retrospective.record.id,
        settled_at=retrospective_target.game_date.replace(tzinfo=UTC) + timedelta(hours=3),
    )

    report = build_frozen_evidence_report(db)

    assert retrospective.record.generation_provenance == RETROSPECTIVE_ASOF
    assert report["provenance"][PROSPECTIVE_FROZEN]["record_count"] == 1
    assert report["provenance"][PROSPECTIVE_FROZEN]["settled_count"] == 1
    assert report["provenance"][RETROSPECTIVE_ASOF]["settled_count"] == 1
    assert report["provenance"][PROSPECTIVE_FROZEN]["probability_calibration"]["n"] == 1
    assert report["readiness_checkpoints"]["25"] == {
        "status": "PENDING",
        "remaining": 24,
    }