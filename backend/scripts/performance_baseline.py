import json
from datetime import datetime
from pathlib import Path
from time import perf_counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient

from app.auth.dependencies import require_viewer
from app.auth.schemas import AuthUser
from app.database.base import Base
from app.database.query_metrics import query_counter
from app.database.session import SessionLocal, engine
from app.main import app
from app.models.game import Game
from app.models.team import Team
from app.models.team_performance import TeamPerformance
from app.repositories import game_repository
from app.scheduler.job_scheduler import JobScheduler
from app.services.dashboard_service import DashboardService
from app.services.prediction_service import PredictionService


GOALS = {
    "prediction_generation_ms_per_game": 100,
    "dashboard_load_ms": 500,
    "api_response_ms_typical": 250,
    "database_query_count": "minimize",
}


def _ensure_output_file() -> Path:
    output_dir = Path(__file__).resolve().parents[1] / "performance"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "baseline.json"


def _timed_call(fn):
    started = perf_counter()
    result = fn()
    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    return result, elapsed_ms


def run() -> dict:
    baseline = {
        "goals": GOALS,
        "metrics": {},
        "notes": [],
        "source": "postgres",
    }

    db = SessionLocal()
    service = PredictionService()
    scheduler = JobScheduler()

    try:
        with query_counter(engine) as prediction_queries:
            games = game_repository.get_games(db)
            game = games[0] if games else None
            if game is None:
                baseline["notes"].append("No games found; prediction_generation benchmark skipped.")
                baseline["metrics"]["prediction_generation_ms_per_game"] = None
            else:
                _, prediction_ms = _timed_call(lambda: service.generate_prediction(db, game.id))
                baseline["metrics"]["prediction_generation_ms_per_game"] = prediction_ms
        baseline["metrics"]["prediction_generation_query_count"] = prediction_queries["value"]

        app.dependency_overrides[require_viewer] = lambda: AuthUser(
            id=1,
            username="perf",
            email="perf@example.com",
            role="admin",
            is_active=True,
        )

        client = TestClient(app)
        with query_counter(engine) as dashboard_queries:
            response, dashboard_ms = _timed_call(lambda: client.get("/api/v1/dashboard"))
            baseline["metrics"]["dashboard_load_ms"] = dashboard_ms
            baseline["metrics"]["dashboard_status_code"] = response.status_code
        baseline["metrics"]["dashboard_query_count"] = dashboard_queries["value"]

        with query_counter(engine) as api_queries:
            response, api_ms = _timed_call(lambda: client.get("/api/v1/analytics/accuracy"))
            baseline["metrics"]["api_response_ms_typical"] = api_ms
            baseline["metrics"]["api_typical_status_code"] = response.status_code
        baseline["metrics"]["api_typical_query_count"] = api_queries["value"]

        with query_counter(engine) as scheduler_queries:
            _, scheduler_ms = _timed_call(lambda: scheduler.run(db, sport="basketball_nba"))
            baseline["metrics"]["scheduler_run_ms_by_league"] = {
                "basketball_nba": scheduler_ms,
            }
        baseline["metrics"]["scheduler_query_count"] = scheduler_queries["value"]

    except Exception as error:
        baseline["notes"].append(f"Postgres baseline failed: {error}")
        baseline = _run_sqlite_fallback(baseline)
    finally:
        app.dependency_overrides.clear()
        db.close()

    output_file = _ensure_output_file()
    output_file.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    return baseline

def _run_sqlite_fallback(existing_baseline: dict) -> dict:
    sqlite_engine = create_engine("sqlite+pysqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
    Base.metadata.create_all(bind=sqlite_engine)

    db = TestingSessionLocal()
    service = PredictionService()
    dashboard = DashboardService()

    baseline = {
        **existing_baseline,
        "source": "sqlite-fallback",
    }

    try:
        _seed_sqlite_data(db)

        with query_counter(sqlite_engine) as prediction_queries:
            first_game = game_repository.get_games(db)[0]
            _, prediction_ms = _timed_call(lambda: service.generate_prediction(db, first_game.id))
            baseline["metrics"]["prediction_generation_ms_per_game"] = prediction_ms
        baseline["metrics"]["prediction_generation_query_count"] = prediction_queries["value"]

        with query_counter(sqlite_engine) as dashboard_queries:
            _, dashboard_ms = _timed_call(lambda: dashboard.get_dashboard(db))
            baseline["metrics"]["dashboard_load_ms"] = dashboard_ms
        baseline["metrics"]["dashboard_query_count"] = dashboard_queries["value"]

        app.dependency_overrides[require_viewer] = lambda: AuthUser(
            id=1,
            username="perf",
            email="perf@example.com",
            role="admin",
            is_active=True,
        )
        client = TestClient(app)
        response, api_ms = _timed_call(lambda: client.get("/health"))
        baseline["metrics"]["api_response_ms_typical"] = api_ms
        baseline["metrics"]["api_typical_status_code"] = response.status_code

        class _ImportService:
            def import_games(self, _db, _sport):
                return game_repository.get_games(_db)

        class _OutcomeService:
            def evaluate_completed_games(self, _db):
                return []

            def update_prediction_metrics(self, _db):
                return {"winner_accuracy": 0.0, "total_outcomes": 0}

        class _DatasetService:
            def build_dataset(self, *args, **kwargs):
                return []

            def validate_dataset(self, dataset):
                return {"valid": True, "records": len(dataset), "errors": []}

        class _TrainingService:
            def evaluate_candidate_models(self, games):
                return []

        scheduler = JobScheduler(
            import_service=_ImportService(),
            prediction_service=service,
            outcome_service=_OutcomeService(),
            dataset_service=_DatasetService(),
            training_service=_TrainingService(),
        )

        with query_counter(sqlite_engine) as scheduler_queries:
            _, scheduler_ms = _timed_call(lambda: scheduler.run(db, sport="basketball_nba"))
            baseline["metrics"]["scheduler_run_ms_by_league"] = {"basketball_nba": scheduler_ms}
        baseline["metrics"]["scheduler_query_count"] = scheduler_queries["value"]
    except Exception as error:
        baseline["notes"].append(f"SQLite fallback failed: {error}")
    finally:
        app.dependency_overrides.clear()
        db.close()

    return baseline


def _seed_sqlite_data(db):
    home_team = Team(name="Home Team", league="NBA", sport="basketball", power_rating=90.0)
    away_team = Team(name="Away Team", league="NBA", sport="basketball", power_rating=88.0)
    db.add_all([home_team, away_team])
    db.flush()

    db.add_all(
        [
            TeamPerformance(
                team_id=home_team.id,
                wins=8,
                losses=2,
                offensive_rating=113.5,
                defensive_rating=105.2,
                recent_form=81.0,
            ),
            TeamPerformance(
                team_id=away_team.id,
                wins=6,
                losses=4,
                offensive_rating=109.1,
                defensive_rating=107.4,
                recent_form=67.0,
            ),
        ]
    )

    db.add(
        Game(
            sport="basketball",
            league="NBA",
            season=2026,
            provider_game_id="baseline-game-1",
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            game_date=datetime(2026, 8, 1, 19, 0, 0),
        )
    )
    db.commit()


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))