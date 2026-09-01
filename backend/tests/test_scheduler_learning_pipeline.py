from datetime import datetime
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.team import Team
from app.scheduler.job_scheduler import JobScheduler
from app.services.prediction_engine import PredictionEngine


class _Monitor:
    def __init__(self):
        self.calls = []

    def log_scheduler(self, message, **context):
        self.calls.append((message, context))


def test_scheduler_handles_missing_outcomes_and_continues_learning_steps():
    class _ImportService:
        def import_games(self, _db, _sport):
            class _Game:
                id = 9

            return [_Game()]

    class _PredictionEngine:
        def __init__(self):
            self.calls = []

        def analyze_markets(self, _db, game_id, persist=True):
            self.calls.append((game_id, persist))
            return [
                f"{game_id}-spread",
                f"{game_id}-moneyline",
                f"{game_id}-total",
            ]

    class _OutcomeService:
        def evaluate_completed_games(self, _db):
            return []

        def update_prediction_metrics(self, _db):
            return {"winner_accuracy": 0.0, "total_outcomes": 0}

    class _DatasetService:
        def __init__(self):
            self.build_calls = 0

        def build_dataset(self, *args, **kwargs):
            self.build_calls += 1
            return []

        def validate_dataset(self, dataset):
            return {"valid": True, "records": len(dataset), "errors": []}

    class _TrainingService:
        def __init__(self):
            self.calls = 0

        def evaluate_candidate_models(self, games):
            self.calls += 1
            assert games == []
            return []

    monitor = _Monitor()
    dataset_service = _DatasetService()
    training_service = _TrainingService()
    prediction_engine = _PredictionEngine()

    scheduler = JobScheduler(
        import_service=_ImportService(),
        prediction_engine=prediction_engine,
        outcome_service=_OutcomeService(),
        dataset_service=dataset_service,
        training_service=training_service,
        monitor=monitor,
    )

    predictions = scheduler.run(db=object(), sport="wnba")

    assert predictions == [
        "9-spread",
        "9-moneyline",
        "9-total",
    ]
    assert prediction_engine.calls == [(9, True)]
    assert dataset_service.build_calls == 1
    assert training_service.calls == 1
    assert any(call[0] == "Evaluated completed games" for call in monitor.calls)


def test_scheduler_prediction_generation_is_idempotent_with_provenance():
    database_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=database_engine)
    db = sessionmaker(bind=database_engine)()

    home_team = Team(name="Home Team", sport="NCAAF", league="NCAAF")
    away_team = Team(name="Away Team", sport="NCAAF", league="NCAAF")
    db.add_all([home_team, away_team])
    db.flush()
    game = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2026,
        provider_game_id="scheduler-idempotency-game",
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        game_date=datetime(2026, 9, 5, 19, 30),
    )
    db.add(game)
    db.flush()
    db.add(
        Odds(
            game_id=game.id,
            sportsbook="Test Sportsbook",
            spread_home=-7.5,
            spread_away=7.5,
            moneyline_home=-280,
            moneyline_away=230,
            total=52.5,
        )
    )
    db.commit()

    prediction_engine = PredictionEngine()
    prediction_engine.model_runtime = MagicMock()
    prediction_engine.model_runtime.resolve.side_effect = ValueError(
        "No production model configured for sport: NCAAF"
    )
    prediction_engine.npi_engine = MagicMock()
    prediction_engine.npi_engine.calculate.return_value = {
        "npi_score": 110,
        "factors": [],
    }
    prediction_engine.ai_engine = MagicMock()
    prediction_engine.ai_engine.generate_analysis.return_value = {
        "engine_version": "test",
        "summary": "Scheduler idempotency test",
        "explanation": "Scheduler idempotency test",
    }

    scheduler = JobScheduler(prediction_engine=prediction_engine)
    first = scheduler._generate_predictions(db, [game])
    second = scheduler._generate_predictions(db, [game])

    predictions = (
        db.query(Prediction)
        .filter(Prediction.game_id == game.id)
        .all()
    )
    assert len(first) == len(second) == 3
    assert len(predictions) == 3
    assert {prediction.market for prediction in predictions} == {
        "spread",
        "moneyline",
        "total",
    }
    for prediction in predictions:
        assert prediction.odds_snapshot_id is not None
        assert prediction.sportsbook is not None
        assert prediction.odds_observed_at is not None