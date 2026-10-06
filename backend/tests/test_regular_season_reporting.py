import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.auth.dependencies import require_analyst, require_viewer
from app.models.game import Game
from app.models.team import Team
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.npi_factor_result import NPIFactorResult
from app.models.nik_score import NikScore
from app.models.prediction_outcome import PredictionOutcome
from app.models.prediction_snapshot import PredictionSnapshot
from app.models.prediction_evaluation import PredictionEvaluation
from app.models.feature_snapshot import FeatureSnapshot
from app.models.backtest_result import BacktestResult
from app.models.model_performance import ModelPerformance
from app.models.model_version import ModelVersion
from app.repositories import prediction_repository
from app.services.analytics.analytics_service import AnalyticsService
from app.services.analytics.backtest_service import BacktestService
from app.services.backtest_engine import BacktestEngine
from app.services.dashboard_service import DashboardService
from app.services.feature_importance_service import FeatureImportanceService
from app.services.model_evaluation import ModelEvaluation
from app.services.model_promotion_service import ModelPromotionService
from app.services.performance_scope import regular_model_metrics
from app.services.training_dataset_service import TrainingDatasetService
from app.services.cache_service import cache_service


@pytest.fixture
def db():
    url = os.getenv("METRIC_TEST_POSTGRES_URL")
    admin = None
    schema = None
    if url:
        target = make_url(url)
        if (
            target.get_backend_name() != "postgresql"
            or target.host not in {"localhost", "127.0.0.1"}
            or target.database != "metric_integrity_test"
        ):
            pytest.fail("Phase tests permit only loopback metric_integrity_test")
        admin = create_engine(url)
        schema = f"phase_test_{uuid4().hex}"
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
    try:
        Base.metadata.create_all(engine, tables=[
            model.__table__ for model in (
                Team, Game, Odds, Prediction, NPIFactorResult, NikScore, PredictionOutcome,
                PredictionSnapshot, PredictionEvaluation, FeatureSnapshot,
                BacktestResult, ModelPerformance, ModelVersion,
            )
        ] + [Base.metadata.tables["prediction_results"]])
        session = sessionmaker(bind=engine)()
        cache_service.clear()
        try:
            yield session
        finally:
            session.close()
            cache_service.clear()
    finally:
        engine.dispose()
        if admin is not None:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


def seed(db, *, preseason_only=False):
    teams = [Team(name=name, sport="NBA", league="NBA") for name in ("Home", "Away")]
    db.add_all(teams)
    db.flush()
    games = []
    phases = ["NBA_PRESEASON"] if preseason_only else ["NBA", "NBA_PRESEASON"]
    for phase in phases:
        pre = phase == "NBA_PRESEASON"
        game = Game(
            sport="NBA", league=phase, provider_game_id=phase,
            home_team_id=teams[0].id, away_team_id=teams[1].id,
            game_date=datetime.now() - timedelta(days=1), status="final",
            home_score=110, away_score=100, winner_team_id=teams[0].id,
        )
        db.add(game)
        db.flush()
        games.append(game)
        db.add(Odds(
            game_id=game.id, sportsbook="Test", spread_home=-3.5, spread_away=3.5,
            moneyline_home=-150, moneyline_away=130, total=205,
        ))
        prediction = Prediction(
            game_id=game.id, market="spread", selection="HOME", model_version="NPI-5.0",
            line_value=-3.5, american_odds=-110, npi_score=100, confidence_score=80,
        )
        db.add(prediction)
        db.flush()
        db.add(NPIFactorResult(
            prediction_id=prediction.id, factor_name="Shared factor", weight=100,
            factor_score=99 if pre else 10, predicted_side="HOME",
            actual_outcome="AWAY" if pre else "HOME",
        ))
        nik = NikScore(game_id=game.id, model_version="test-model", confidence=99 if pre else 60)
        snapshot = PredictionSnapshot(
            game_id=game.id, model_version="test-model", prediction=str(teams[0].id),
            confidence=99 if pre else 60, home_score=110, away_score=100,
            home_features={"momentum": 99 if pre else 60},
        )
        db.add_all([nik, snapshot])
        db.flush()
        db.add_all([
            PredictionOutcome(
                game_id=game.id, prediction_id=nik.id, predicted_winner="HOME",
                actual_winner="AWAY" if pre else "HOME", predicted_confidence=99 if pre else 60,
                prediction_correct=not pre,
            ),
            FeatureSnapshot(
                prediction_id=nik.id, model_version="test-model",
                feature_name="home_strength", feature_value=99 if pre else 60,
            ),
            PredictionEvaluation(
                snapshot_id=snapshot.id, correct=not pre, predicted_team=str(teams[0].id),
                actual_winner=teams[1].id if pre else teams[0].id, confidence=99 if pre else 60,
            ),
            BacktestResult(
                backtest_id=1, game_id=game.id, model_version="test-model", sport="NBA",
                market="spread", outcome="LOSS" if pre else "WIN",
                win_loss="LOSS" if pre else "WIN", confidence=99 if pre else 60,
                profit_loss=-1 if pre else 1, accuracy=0 if pre else 100, roi=-100 if pre else 100,
            ),
        ])
    db.add_all([
        BacktestResult(
            backtest_id=2, model_version="unverified", sport="NBA", market="summary",
            outcome="WIN", win_loss="WIN", profit_loss=9999, total_predictions=9999,
        ),
        ModelPerformance(model_version="unverified", accuracy=99, total_predictions=9999),
        ModelVersion(
            model_name="test-model", version="test-model", sport="NBA",
            overall_accuracy=99, ats_accuracy=99, games_evaluated=9999,
        ),
    ])
    db.commit()
    return games


def client(db, *routers):
    app = FastAPI()
    for router in routers:
        app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_analyst] = lambda: SimpleNamespace(role="admin")
    app.dependency_overrides[require_viewer] = lambda: SimpleNamespace(role="admin")
    return TestClient(app)


@pytest.mark.parametrize("preseason_only", [False, True])
def test_factor_services_and_default_endpoint_exclude_preseason(db, preseason_only):
    from app.api.v1 import model
    seed(db, preseason_only=preseason_only)
    summary = ModelEvaluation().factor_summary(db)
    rates = ModelEvaluation().factor_win_rates(db)
    assert summary == ([] if preseason_only else [
        {"factor": "Shared factor", "games": 1, "average_score": 10.0},
    ])
    assert rates == ([] if preseason_only else [{"factor": "Shared factor", "win_rate": 100.0}])
    response = client(db, model.router).get("/api/v1/model/factors")
    assert response.status_code == 200
    assert response.json()["top_factors"] == rates
    assert response.json()["overall_accuracy"] == (0 if preseason_only else 100)
    assert response.json()["ats_accuracy"] == (0 if preseason_only else 100)
    assert db.query(ModelVersion).one().games_evaluated == 9999
    assert db.query(NPIFactorResult).count() == (1 if preseason_only else 2)


@pytest.mark.parametrize("preseason_only", [False, True])
def test_backtest_creation_summaries_versions_and_promotion(db, preseason_only):
    from app.api.v1 import backtests, model_promotion
    games = seed(db, preseason_only=preseason_only)
    engine = BacktestEngine(prediction_engine=MagicMock())
    engine.prediction_engine.analyze_game.return_value = SimpleNamespace(
        selection="HOME", npi_score=100, confidence_score=80, projected_edge=5,
    )
    expected = 0 if preseason_only else 1
    run = engine.run(db, "run-model", games[0].game_date.date(), games[0].game_date.date(), sport="NBA")
    assert run["games_stored"] == expected
    assert engine.prediction_engine.analyze_game.call_count == expected
    summary = engine.run_summary(db, 1)
    assert summary == {} if preseason_only else summary["games"] == 1
    assert engine.run_summary(db, 2) == {}
    comparison = engine.version_comparison(db)
    assert len(comparison) == (0 if preseason_only else 2)
    assert all(row["ats"] == 100 for row in comparison)
    promotion = ModelPromotionService().evaluate_candidate(db, "test-model", "NBA")
    assert promotion["games"] == expected
    assert promotion["ats_win_rate"] == (0 if preseason_only else 100)
    api = client(db, backtests.router, model_promotion.router)
    result = api.get("/api/v1/backtests")
    assert result.status_code == 200
    assert len(result.json()["runs"]) == (0 if preseason_only else 2)
    assert api.get("/api/v1/models/evaluate/NBA/test-model").json()["games"] == expected
    assert db.query(BacktestResult).filter(BacktestResult.game_id.is_(None)).count() == 1


@pytest.mark.parametrize("preseason_only", [False, True])
def test_snapshot_analytics_replay_and_training_boundaries(db, preseason_only):
    games = seed(db, preseason_only=preseason_only)
    expected = 0 if preseason_only else 1
    regular_ids = set() if preseason_only else {games[0].id}
    for query in (
        prediction_repository.get_snapshots, prediction_repository.get_recent_snapshots,
        prediction_repository.get_snapshots_with_completed_games,
    ):
        assert {row.game_id for row in query(db, limit=1)} == regular_ids
    raw = prediction_repository.get_latest_snapshot_for_game(db, games[-1].id)
    assert raw.game_id == games[-1].id
    importance = FeatureImportanceService().historical_importance(db)
    assert importance == [] if preseason_only else next(
        row["average_contribution"] for row in importance if row["feature"] == "Momentum"
    ) == 2.5
    service = BacktestService()
    result = service.create_result(db, "test-model", db.query(PredictionEvaluation).all(), sport="NBA")
    assert result.total_predictions == expected
    assert result.accuracy == (0 if preseason_only else 100)
    assert result.average_confidence == (0 if preseason_only else 60)
    assert len(service.replay(db, db.query(PredictionSnapshot).all())) == expected
    dataset = TrainingDatasetService().build_dataset(
        datetime.now() - timedelta(days=3), datetime.now() + timedelta(days=1), db=db,
    )
    assert len(dataset) == expected
    assert all(row["confidence"] == 60 for row in dataset)
    analytics = AnalyticsService()
    assert analytics._safe_training_sample_count(db) == expected
    summary = analytics.dashboard_statistics(db)
    assert {row["game_id"] for row in summary["recent_predictions"]} == regular_ids
    assert summary["model_learning"]["training_samples"] == expected
    assert len(regular_model_metrics(db).all()) == expected
    lab = DashboardService()._model_lab_summary(db)
    assert lab is None if preseason_only else lab["current"]["model_version"] == "test-model"
    assert db.query(ModelPerformance).one().model_version == "unverified"


@pytest.mark.parametrize("preseason_only", [False, True])
def test_production_model_and_analytics_endpoints_ignore_unverified_aggregates(db, preseason_only):
    from app.api.v1 import models, analytics
    seed(db, preseason_only=preseason_only)
    api = client(db, models.router, analytics.router)
    response = api.get("/api/v1/models")
    assert response.status_code == 200
    payload = response.json()
    assert payload == [] if preseason_only else payload[0]["evaluation_metrics"] == {
        "accuracy": 100.0, "calibration": 0.0, "average_confidence": 60.0, "predictions": 1,
    }
    assert api.get("/api/v1/models/unverified").status_code == 404
    assert api.get("/api/v1/models/test-model").status_code == (404 if preseason_only else 200)
    compared = api.post("/api/v1/models/compare", json={
        "current_version": "test-model", "candidate_version": "test-model",
    })
    assert compared.status_code == (404 if preseason_only else 200)
    accuracy = api.get("/api/v1/analytics/accuracy")
    assert accuracy.status_code == 200
    history = accuracy.json()["dashboard_statistics"]["recent_predictions"]
    assert len(history) == (0 if preseason_only else 1)
    assert api.get("/api/v1/analytics/calibration").json()["total_predictions"] == (0 if preseason_only else 1)
    assert db.query(ModelPerformance).count() == 1


@contextmanager
def capture_reporting_queries(db):
    selects = []
    loaded_backtests = []

    def capture(_connection, _cursor, statement, parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append((statement, parameters))

    def loaded(row, _context):
        loaded_backtests.append(row.id)

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    event.listen(BacktestResult, "load", loaded)
    try:
        yield selects, loaded_backtests
    finally:
        event.remove(engine, "before_cursor_execute", capture)
        event.remove(BacktestResult, "load", loaded)


def add_reporting_game(db, source, sport, league):
    game = Game(
        sport=sport, league=league, provider_game_id=f"{sport}-{uuid4().hex}",
        home_team_id=source.home_team_id, away_team_id=source.away_team_id,
        game_date=source.game_date, status="final", home_score=110, away_score=100,
        winner_team_id=source.home_team_id,
    )
    db.add(game)
    db.flush()
    return game


def add_reporting_outcome(db, game_id, version, correct):
    prediction = NikScore(game_id=game_id, model_version=version, confidence=80)
    db.add(prediction)
    db.flush()
    db.add(PredictionOutcome(
        game_id=game_id, prediction_id=prediction.id, predicted_winner="HOME",
        actual_winner="HOME" if correct else "AWAY",
        predicted_confidence=80, prediction_correct=correct,
    ))


def test_model_factor_endpoint_scopes_sport_version_phase_and_bounds_history_reads(db):
    from app.api.v1 import model
    regular, preseason = seed(db)
    add_reporting_outcome(db, regular.id, "test-model", False)
    db.add_all([
        BacktestResult(
            backtest_id=3, game_id=regular.id, model_version="test-model",
            sport="NBA", market="spread", win_loss=outcome, outcome=outcome.upper(),
        )
        for outcome in ("win", "PUSH")
    ])
    nfl = add_reporting_game(db, regular, "NFL", "NFL")
    nfl_id, regular_id, preseason_id = nfl.id, regular.id, preseason.id
    db.commit()
    api = client(db, model.router)
    baseline_query_count = None
    for game_id, version, count in (
        (None, None, 0),
        (nfl_id, "test-model", 1),
        (nfl_id, "test-model", 1000),
        (regular_id, "unrelated-model", 1000),
        (preseason_id, "test-model", 1000),
    ):
        if game_id is not None:
            add_reporting_outcome(db, game_id, version, False)
            db.add_all([
                BacktestResult(
                    backtest_id=4, game_id=game_id, model_version=version,
                    sport="NFL" if game_id == nfl_id else "NBA",
                    market="spread", win_loss="LOSS", outcome="LOSS",
                )
                for _ in range(count)
            ])
            db.commit()
        db.expunge_all()
        with capture_reporting_queries(db) as (selects, loaded):
            response = api.get("/api/v1/model/factors")
        assert response.status_code == 200
        assert response.json()["version"] == "test-model"
        assert response.json()["overall_accuracy"] == 50.0
        assert response.json()["ats_accuracy"] == 66.67
        assert loaded == []
        backtest_selects = [
            sql for sql, _parameters in selects if "FROM backtest_results" in sql
        ]
        assert len(backtest_selects) == 1
        sql = backtest_selects[0]
        assert "count(backtest_results.id)" in sql
        assert "sum(CASE" in sql
        where = sql.split("WHERE", 1)[1]
        assert "games.sport =" in where
        assert "backtest_results.model_version =" in where
        assert "games.league !=" in where
        outcome_sql = next(sql for sql, _ in selects if "FROM prediction_outcomes" in sql)
        where = outcome_sql.split("WHERE", 1)[1].split("GROUP BY", 1)[0]
        assert "games.sport =" in where
        assert "nik_scores.model_version =" in where
        assert "games.league !=" in where
        if baseline_query_count is None:
            baseline_query_count = len(selects)
        assert len(selects) == baseline_query_count


@pytest.mark.parametrize("snapshot_count", [1, 10, 100])
def test_replay_phase_filter_adds_no_per_snapshot_queries(db, snapshot_count):
    regular, preseason = seed(db)
    snapshots = [
        PredictionSnapshot(
            game_id=regular.id, model_version="replay-test",
            prediction=str(regular.winner_team_id), confidence=75,
        )
        for _ in range(snapshot_count)
    ]
    direct_preseason = PredictionSnapshot(
        game_id=preseason.id, model_version="replay-test",
        prediction=str(preseason.winner_team_id), confidence=99,
    )
    db.add_all([*snapshots, direct_preseason])
    db.commit()
    regular_ids = {row.id for row in snapshots}
    preseason_id = direct_preseason.id
    with capture_reporting_queries(db) as (selects, _loaded):
        evaluations = BacktestService().replay(db, [*snapshots, direct_preseason])
    assert {row.snapshot_id for row in evaluations} == regular_ids
    phase_only = [
        sql for sql, _parameters in selects
        if "FROM games" in sql and "WHERE" in sql and "games.league" in sql.split("WHERE", 1)[1]
    ]
    assert phase_only == []
    assert db.query(PredictionEvaluation).filter(
        PredictionEvaluation.snapshot_id == preseason_id,
    ).count() == 0
    assert BacktestService().replay(db, [direct_preseason]) == []


@pytest.mark.parametrize("sport", ["NFL", "NCAAF", "NCAAB", "WNBA"])
def test_replay_retains_each_non_nba_sport(db, sport):
    source = seed(db)[0]
    game = add_reporting_game(db, source, sport, sport)
    snapshot = PredictionSnapshot(
        game_id=game.id, model_version="replay-test",
        prediction=str(game.winner_team_id), confidence=75,
    )
    db.add(snapshot)
    db.commit()
    evaluations = BacktestService().replay(db, [snapshot])
    assert len(evaluations) == 1
    assert evaluations[0].snapshot_id == snapshot.id
    assert evaluations[0].correct is True
