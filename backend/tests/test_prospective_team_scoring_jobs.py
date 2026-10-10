import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import scripts.evaluate_prospective_team_scoring as evaluator
from app.database.base import Base
from app.models.game import Game
from app.models.game_provider_identity import GameProviderIdentity
from app.models.game_result_observation import GameResultObservation
from app.models.team import Team
from app.models.team_provider_identity import TeamProviderIdentity
from app.services.team_scoring_forecast import TimestampedScore
from scripts.evaluate_prospective_team_scoring import (
    _primary_attempts,
    build_evaluation_metrics,
    build_settlement_events,
)
from scripts.import_prospective_cfbd_scores import collect_scores
from scripts.record_prospective_team_scoring import (
    _load_prior_records,
    _score_observations,
    _write_attempt_batch,
)


def _database():
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
            GameResultObservation.__table__,
            TeamProviderIdentity.__table__,
            GameProviderIdentity.__table__,
        ],
    )
    return engine, sessionmaker(bind=engine)()


def _attempt(
    *,
    game_id=41,
    run_id="run-one",
    timestamp="2026-10-10T01:00:00+00:00",
    margin=6.0,
    valid=True,
):
    kickoff = datetime.fromisoformat(timestamp) + timedelta(days=1)
    return {
        "record_type": "candidate_forecast_attempt",
        "protocol_version": "TEAM-SCORING-PROSPECTIVE-1.0",
        "candidate_model_version": "TEAM-SCORING-RIDGE-1.0",
        "candidate_margin_available": valid,
        "candidate_home_margin": margin if valid else None,
        "prediction_timestamp": timestamp,
        "run_id": run_id,
        "game_id": game_id,
        "sport": "NCAAF",
        "kickoff": kickoff.isoformat(),
        "spread_home": -3.5,
        "spread_away": 3.5,
        "spread_home_price": -110,
        "spread_away_price": -110,
        "cover_probability": {
            "home_cover": 0.55,
            "away_cover": 0.40,
            "push": 0.05,
            "calibration_games": 30,
        },
        "shadow_selection": {
            "side": "HOME",
            "expected_value_per_unit": 0.1,
        },
        "history_observation_inputs": [],
    }


def _score(
    *,
    observation_id=501,
    observed_at="2026-10-11T03:00:00+00:00",
    home_score=24,
    away_score=20,
):
    return TimestampedScore(
        game_id=41,
        sport="NCAAF",
        home_team_id=1,
        away_team_id=2,
        kickoff=datetime(2026, 10, 11, 1, tzinfo=UTC),
        observed_at=datetime.fromisoformat(observed_at),
        neutral_site=False,
        home_score=home_score,
        away_score=away_score,
        status="final",
        observation_id=observation_id,
        source_provider="odds_api",
    )


def test_primary_attempt_uses_first_available_frozen_forecast_per_game():
    no_margin = _attempt(
        run_id="earliest-no-margin", timestamp="2026-10-10T00:00:00+00:00", valid=False
    )
    first = _attempt(
        run_id="first-margin", timestamp="2026-10-10T01:00:00+00:00", margin=6.0
    )
    repeated = _attempt(
        run_id="later-margin", timestamp="2026-10-10T02:00:00+00:00", margin=99.0
    )

    primary = _primary_attempts([no_margin, first, repeated])

    assert primary[41]["run_id"] == "first-margin"
    assert primary[41]["candidate_home_margin"] == 6.0


def test_settlement_is_idempotent_and_score_corrections_are_append_only():
    attempts = [
        _attempt(run_id="primary", timestamp="2026-10-10T01:00:00+00:00"),
        _attempt(run_id="revision", timestamp="2026-10-10T02:00:00+00:00", margin=50.0),
    ]
    first_score = _score()
    now = datetime(2026, 10, 12, tzinfo=UTC)

    first_events, first_latest = build_settlement_events(
        attempts, [first_score], as_of=now, existing_events=[]
    )
    assert len(first_events) == 1
    assert first_events[0]["selected_outcome"] == "WIN"
    assert first_latest[41]["primary_attempt_id"] == "primary:41"
    assert first_events[0]["customer_recommendation"] is False

    repeated_events, _ = build_settlement_events(
        attempts, [first_score], as_of=now, existing_events=first_events
    )
    assert repeated_events == []

    corrected_score = _score(
        observation_id=502,
        observed_at="2026-10-12T00:00:00+00:00",
        home_score=20,
        away_score=24,
    )
    correction, latest = build_settlement_events(
        attempts,
        [first_score, corrected_score],
        as_of=datetime(2026, 10, 12, 0, 30, tzinfo=UTC),
        existing_events=first_events,
    )
    assert len(correction) == 1
    assert correction[0]["is_score_correction"] is True
    assert correction[0]["supersedes_score_observation_id"] == 501
    assert correction[0]["selected_outcome"] == "LOSS"
    assert latest[41]["score_observation_id"] == 502
    assert (
        build_evaluation_metrics(first_events + correction)["NCAAF"][
            "unique_settled_games"
        ]
        == 1
    )


def test_settlement_requires_actual_postkick_receipt_and_rejects_unverified_history():
    attempt = _attempt()
    too_early = _score(observed_at="2026-10-10T22:00:00+00:00")
    events, _ = build_settlement_events(
        [attempt],
        [too_early],
        as_of=datetime(2026, 10, 12, tzinfo=UTC),
        existing_events=[],
    )
    assert events == []

    unverified = _attempt()
    unverified["history_observation_inputs"] = [
        {
            "source_provider": "cfbd",
            "observed_at": "2020-01-01T00:00:00+00:00",
        }
    ]
    valid_score = _score()
    rejected, _ = build_settlement_events(
        [unverified],
        [valid_score],
        as_of=datetime(2026, 10, 12, tzinfo=UTC),
        existing_events=[],
    )
    assert rejected == []


def test_cfbd_rows_with_source_dates_are_excluded_from_future_forecast_inputs():
    engine, db = _database()
    try:
        home = Team(name="Home", sport="NCAAF", league="NCAAF")
        away = Team(name="Away", sport="NCAAF", league="NCAAF")
        db.add_all([home, away])
        db.flush()
        game = Game(
            sport="NCAAF",
            league="NCAAF",
            home_team_id=home.id,
            away_team_id=away.id,
            game_date=datetime(2026, 10, 1, tzinfo=UTC),
            status="final",
            neutral_site=True,
        )
        db.add(game)
        db.flush()
        db.add_all(
            [
                GameResultObservation(
                    game_id=game.id,
                    provider="cfbd",
                    home_score=21,
                    away_score=17,
                    status="final",
                    observed_at=datetime(2020, 1, 1, tzinfo=UTC),
                ),
                GameResultObservation(
                    game_id=game.id,
                    provider="odds_api",
                    home_score=21,
                    away_score=17,
                    status="final",
                    observed_at=datetime(2026, 10, 2, tzinfo=UTC),
                ),
            ]
        )
        db.commit()

        observations = _score_observations(db)

        assert len(observations) == 1
        assert observations[0].source_provider == "odds_api"
        assert observations[0].receipt_basis == "provider_observed_at"
    finally:
        db.close()
        engine.dispose()


def test_cfbd_shadow_import_uses_receipt_time_and_is_idempotent(tmp_path):
    engine, db = _database()
    try:
        home = Team(name="Home", sport="NCAAF", league="NCAAF")
        away = Team(name="Away", sport="NCAAF", league="NCAAF")
        db.add_all([home, away])
        db.flush()
        db.add_all(
            [
                TeamProviderIdentity(
                    team_id=home.id,
                    provider="cfbd",
                    sport="NCAAF",
                    provider_team_id="101",
                    provider_name="Home",
                ),
                TeamProviderIdentity(
                    team_id=away.id,
                    provider="cfbd",
                    sport="NCAAF",
                    provider_team_id="202",
                    provider_name="Away",
                ),
            ]
        )
        existing_game = Game(
            sport="NCAAF",
            league="NCAAF",
            home_team_id=home.id,
            away_team_id=away.id,
            game_date=datetime(2026, 10, 3, 18, tzinfo=UTC),
            status="final",
        )
        db.add(existing_game)
        db.commit()
        unknown_site = SimpleNamespace(
            id=9002,
            season=2026,
            start_date=datetime(2026, 10, 4, 18, tzinfo=UTC),
            home_id=101,
            away_id=202,
            home_team="Home",
            away_team="Away",
            home_points=10,
            away_points=7,
            completed=True,
            neutral_site=None,
            venue_name=None,
            venue_city=None,
            venue_state=None,
            source_updated_at=datetime(2026, 10, 4, tzinfo=UTC),
        )
        source_game = SimpleNamespace(
            id=9001,
            season=2026,
            start_date=datetime(2026, 10, 3, 18, tzinfo=UTC),
            home_id=101,
            away_id=202,
            home_team="Home",
            away_team="Away",
            home_points=28,
            away_points=21,
            completed=True,
            neutral_site=True,
            venue_name="Stadium",
            venue_city="Town",
            venue_state="ST",
            source_updated_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        requested_seasons = []

        def get_games(season):
            requested_seasons.append(season)
            return [source_game, unknown_site]

        client = SimpleNamespace(get_games=get_games)
        output = tmp_path / "scores.jsonl"

        started = datetime.now(UTC)
        first_report = collect_scores(
            db,
            seasons=(2026,),
            output=output,
            client=client,
        )
        finished = datetime.now(UTC)
        row = json.loads(output.read_text(encoding="utf-8").splitlines()[0])

        assert started.isoformat() <= row["observed_at"] <= finished.isoformat()
        assert row["observed_at"] != row["source_updated_at"]
        assert row["receipt_basis"] == "shadow_import_receipt"
        assert row["neutral_site"] is True
        assert row["game_id"] == existing_game.id
        assert first_report["sports"]["NCAAF"]["captured"] == 1
        assert first_report["sports"]["NCAAF"]["unknown_site"] == 1
        assert requested_seasons == [2026]

        second_report = collect_scores(
            db,
            seasons=(2026,),
            output=output,
            client=client,
        )
        assert second_report["observations_appended"] == 0
        assert len(output.read_text(encoding="utf-8").splitlines()) == 1

        source_game.home_points = 17
        source_game.away_points = 21
        source_game.source_updated_at = datetime(2026, 10, 5, tzinfo=UTC)
        correction = collect_scores(
            db,
            seasons=(2026,),
            output=output,
            client=client,
        )
        rows = [
            json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()
        ]
        assert correction["observations_appended"] == 1
        assert rows[-1]["home_score"] == 17
        assert rows[-1]["away_score"] == 21

        repeated_correction = collect_scores(
            db,
            seasons=(2026,),
            output=output,
            client=client,
        )
        assert repeated_correction["observations_appended"] == 0
        assert len(output.read_text(encoding="utf-8").splitlines()) == 2
    finally:
        db.close()
        engine.dispose()


def test_attempt_batches_are_compressed_immutable_and_prior_loader_deduplicated(
    tmp_path,
):
    output = tmp_path / "attempts"
    output.mkdir()
    row = {
        "record_type": "candidate_forecast_attempt",
        "candidate_model_version": "TEAM-SCORING-RIDGE-1.0",
        "candidate_margin_available": True,
        "sport": "NCAAF",
        "game_id": 1,
        "prediction_timestamp": "2026-10-10T01:00:00+00:00",
        "candidate_home_margin": 5.0,
        "history_observation_inputs": [
            {
                "source_provider": "cfbd",
                "receipt_basis": "shadow_import_receipt",
            }
        ],
    }

    first = _write_attempt_batch(output, "hour-one", [row])
    repeated = _write_attempt_batch(output, "hour-one", [row])

    assert first is not None
    assert first.suffix == ".gz"
    assert repeated is None
    assert _load_prior_records(output) == [
        {
            "sport": "NCAAF",
            "candidate_model_version": "TEAM-SCORING-RIDGE-1.0",
            "candidate_margin_available": True,
            "game_id": 1,
            "prediction_timestamp": "2026-10-10T01:00:00+00:00",
            "candidate_home_margin": 5.0,
        }
    ]


@pytest.mark.parametrize("job", ["evaluate", "coverage"])
def test_evaluator_sets_read_only_transaction_before_job_queries(
    monkeypatch, tmp_path, capsys, job
):
    executed = []

    class FakeSession:
        bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, statement):
            executed.append(str(statement))

        def rollback(self):
            executed.append("rollback")

    monkeypatch.setattr(evaluator, "SessionLocal", lambda: FakeSession())
    monkeypatch.setenv("TEAM_SCORING_JOB", job)
    monkeypatch.setenv("TEAM_SCORING_RUN_ID", "test-run")
    monkeypatch.setenv("TEAM_SCORING_EVAL_DIR", str(tmp_path))
    if job == "evaluate":
        monkeypatch.setattr(
            evaluator,
            "run_settlement_job",
            lambda db, **kwargs: executed.append("job") or {},
        )
    else:
        monkeypatch.setattr(
            evaluator,
            "run_coverage_job",
            lambda db, **kwargs: executed.append("job") or {},
        )

    evaluator.main()

    assert executed == [
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ",
        "SET TRANSACTION READ ONLY",
        "job",
        "rollback",
    ]
    assert capsys.readouterr().out.strip() == "{}"
