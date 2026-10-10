from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.import_run import ImportRun
from app.models.odds import Odds
from app.models.team import Team
from scripts.evaluate_prospective_team_scoring import _append_jsonl
from scripts.record_prospective_team_scoring import build_prospective_records

AS_OF = datetime(2026, 10, 9, 23, 50, tzinfo=UTC)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Team.__table__,
            Game.__table__,
            Odds.__table__,
            ImportRun.__table__,
            GameResultObservation.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _naive(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(tzinfo=None)


def _seed_teams(db):
    teams = [
        Team(name=f"Team {index}", sport="NCAAF", league="NCAAF") for index in range(4)
    ]
    db.add_all(teams)
    db.flush()
    return teams


def _add_history(db, teams, *, count=8, as_of=AS_OF):
    observations = []
    for index in range(count):
        kickoff = as_of - timedelta(days=10 - index)
        home_index = index % 4
        away_index = (index + 1) % 4
        game = Game(
            sport="NCAAF",
            league="NCAAF",
            home_team_id=teams[home_index].id,
            away_team_id=teams[away_index].id,
            game_date=_naive(kickoff),
            status="final",
            neutral_site=True,
        )
        db.add(game)
        db.flush()
        observation = GameResultObservation(
            game_id=game.id,
            provider="test",
            home_score=24 + index,
            away_score=17 + index % 3,
            status="final",
            observed_at=_naive(kickoff + timedelta(hours=4)),
        )
        db.add(observation)
        observations.append(observation)
    db.flush()
    return observations


def _add_target(db, teams, *, as_of=AS_OF, neutral_site=True, quote=True):
    game = Game(
        sport="NCAAF",
        league="NCAAF",
        home_team_id=teams[0].id,
        away_team_id=teams[1].id,
        game_date=_naive(as_of + timedelta(days=2)),
        status="scheduled",
        neutral_site=neutral_site,
    )
    db.add(game)
    db.flush()
    if quote:
        db.add(
            Odds(
                game_id=game.id,
                sportsbook="Frozen Book",
                spread_home=-3.5,
                spread_away=3.5,
                spread_home_price=-110,
                spread_away_price=-110,
                created_at=_naive(as_of - timedelta(minutes=5)),
            )
        )
    db.flush()
    return game


def _add_prior_forecast_results(db, teams, *, count=30):
    observations = []
    kickoff = AS_OF - timedelta(days=3)
    for index in range(count):
        game = Game(
            sport="NCAAF",
            league="NCAAF",
            home_team_id=teams[0].id,
            away_team_id=teams[1].id,
            game_date=_naive(kickoff),
            status="final",
            neutral_site=True,
        )
        db.add(game)
        db.flush()
        observation = GameResultObservation(
            game_id=game.id,
            provider="test",
            home_score=30 + index,
            away_score=20 + index % 3,
            status="final",
            observed_at=_naive(AS_OF - timedelta(days=1)),
        )
        db.add(observation)
        observations.append(observation)
    db.flush()
    return observations


def test_records_prepublication_receipt_inputs_and_never_writes_customer_rows(db):
    teams = _seed_teams(db)
    history = _add_history(db, teams)
    target = _add_target(db, teams)
    late_game = Game(
        sport="NCAAF",
        league="NCAAF",
        home_team_id=teams[2].id,
        away_team_id=teams[3].id,
        game_date=_naive(AS_OF - timedelta(days=2)),
        status="final",
        neutral_site=True,
    )
    db.add(late_game)
    db.flush()
    late = GameResultObservation(
        game_id=late_game.id,
        provider="test",
        home_score=50,
        away_score=10,
        status="final",
        observed_at=_naive(AS_OF),
    )
    db.add(late)
    db.commit()

    rows = build_prospective_records(db, as_of=AS_OF)

    record = next(row for row in rows if row["game_id"] == target.id)
    assert record["candidate_margin_available"] is True
    assert record["history_observation_count"] == len(history)
    assert late.id not in record["history_observation_ids"]
    assert record["history_latest_receipt_at"] < AS_OF.isoformat()
    assert all(
        item["observed_at"] < AS_OF.isoformat()
        for item in record["history_observation_inputs"]
    )
    assert {
        item["observation_id"] for item in record["history_observation_inputs"]
    } == set(record["history_observation_ids"])
    assert record["frozen_odds_snapshot_timestamp"] < AS_OF.isoformat()
    assert record["customer_recommendation"] is False
    assert record["candidate_activation_enabled"] is False
    assert record["candidate_model_version"] == "TEAM-SCORING-RIDGE-1.0"
    assert db.query(GameResultObservation).count() == len(history) + 1
    assert not db.new
    assert not db.dirty
    assert not db.deleted


def test_unknown_venue_and_missing_frozen_quote_are_explicit_rejections(db):
    teams = _seed_teams(db)
    _add_history(db, teams)
    target = _add_target(db, teams, neutral_site=None, quote=False)

    rows = build_prospective_records(db, as_of=AS_OF)

    record = next(row for row in rows if row["game_id"] == target.id)
    assert record["candidate_margin_available"] is False
    assert record["neutral_site"] is None
    assert record["rejection_reasons"] == [
        "no_pre_timestamp_odds_snapshot",
        "target_neutral_site_unknown",
    ]
    assert record["candidate_home_margin"] is None


def test_cover_probabilities_use_only_prior_settled_forecast_records(db):
    teams = _seed_teams(db)
    prior_observations = _add_prior_forecast_results(db, teams)
    target = _add_target(db, teams)
    prior_timestamp = AS_OF - timedelta(days=2)
    prior_records = [
        {
            "sport": "NCAAF",
            "candidate_model_version": "TEAM-SCORING-RIDGE-1.0",
            "candidate_margin_available": True,
            "game_id": observation.game_id,
            "prediction_timestamp": prior_timestamp.isoformat(),
            "candidate_home_margin": float(observation.home_score)
            - float(observation.away_score)
            - 1,
        }
        for observation in prior_observations
    ]
    db.commit()

    rows = build_prospective_records(
        db,
        as_of=AS_OF,
        prior_records=prior_records,
    )

    record = next(row for row in rows if row["game_id"] == target.id)
    assert record["candidate_margin_available"] is True
    assert record["cover_probability"]["calibration_games"] == 30
    assert len(record["probability_calibration_sample"]) == 30
    assert all(
        item["score_observed_at"] < AS_OF.isoformat()
        for item in record["probability_calibration_sample"]
    )
    assert (
        record["shadow_selection"] is None or record["customer_recommendation"] is False
    )


def test_prospective_records_append_as_independent_json_lines(tmp_path):
    output = tmp_path / "prospective.jsonl"
    output.write_text('{"prior":true}\n', encoding="utf-8")

    _append_jsonl(output, [{"attempt": 1}, {"attempt": 2}])

    assert output.read_text(encoding="utf-8").splitlines() == [
        '{"prior":true}',
        '{"attempt":1}',
        '{"attempt":2}',
    ]
