from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.game import Game
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.user_prediction import UserPrediction
from app.services.v1_read_service import V1ReadService


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _prediction(
    db,
    *,
    game_id: int,
    market: str,
    selection: str,
    line_value: float | None,
):
    prediction = Prediction(
        game_id=game_id,
        market=market,
        selection=selection,
        line_value=line_value,
        american_odds=-110,
        npi_score=150.0,
        win_probability=60.0,
        projected_edge=7.6,
        confidence_score=80.0,
        risk_level="LOW",
        model_version="NPI-4.0",
    )
    db.add(prediction)
    db.flush()
    return prediction


def _result(db, prediction_id: int, result: str, profit_loss: float):
    row = PredictionResult(
        prediction_id=prediction_id,
        actual_result="HOME",
        predicted_result="HOME",
        outcome=result,
        profit_loss=profit_loss,
    )
    db.add(row)
    db.flush()
    return row


def _dump(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {
        key: getattr(value, key)
        for key in dir(value)
        if not key.startswith("_")
        and not callable(getattr(value, key))
    }


def test_saved_pick_exposes_authoritative_prediction_result_and_is_user_scoped():
    db = _session()

    try:
        home = Team(
            name="Rutgers Scarlet Knights",
            league="NCAAF",
            sport="NCAAF",
        )
        away = Team(
            name="UMass Minutemen",
            league="NCAAF",
            sport="NCAAF",
        )
        db.add_all([home, away])
        db.flush()

        game = Game(
            sport="NCAAF",
            league="NCAAF",
            game_date=datetime.now(timezone.utc),
            home_team_id=home.id,
            away_team_id=away.id,
            home_score=31,
            away_score=21,
        )
        db.add(game)
        db.flush()

        prediction = _prediction(
            db,
            game_id=game.id,
            market="spread",
            selection="HOME",
            line_value=-6.5,
        )

        db.add(
            UserPrediction(
                user_id=101,
                prediction_id=prediction.id,
            )
        )

        _result(
            db,
            prediction_id=prediction.id,
            result="WIN",
            profit_loss=0.91,
        )

        db.commit()

        service = V1ReadService()

        owner_picks = service.get_saved_picks(
            db=db,
            user_id=101,
        )
        other_user_picks = service.get_saved_picks(
            db=db,
            user_id=202,
        )

        assert owner_picks["count"] == 1
        assert other_user_picks == {"count": 0, "picks": []}

        saved = _dump(owner_picks["picks"][0])

        assert saved["prediction_id"] == prediction.id

        serialized = str(saved).upper()

        assert "SPREAD" in serialized
        assert "HOME" in serialized
        assert "WIN" in serialized

    finally:
        db.close()


def test_performance_uses_prediction_results_and_excludes_pushes_from_accuracy():
    db = _session()

    try:
        home = Team(
            name="Rutgers Scarlet Knights",
            league="NCAAF",
            sport="NCAAF",
        )
        away = Team(
            name="UMass Minutemen",
            league="NCAAF",
            sport="NCAAF",
        )
        db.add_all([home, away])
        db.flush()

        game = Game(
            sport="NCAAF",
            league="NCAAF",
            game_date=datetime.now(timezone.utc),
            home_team_id=home.id,
            away_team_id=away.id,
            home_score=31,
            away_score=21,
        )
        db.add(game)
        db.flush()

        win_prediction = _prediction(
            db,
            game_id=game.id,
            market="spread",
            selection="HOME",
            line_value=-6.5,
        )

        loss_prediction = _prediction(
            db,
            game_id=game.id,
            market="moneyline",
            selection="AWAY",
            line_value=None,
        )

        push_prediction = _prediction(
            db,
            game_id=game.id,
            market="total",
            selection="OVER",
            line_value=52.0,
        )

        _result(
            db,
            prediction_id=win_prediction.id,
            result="WIN",
            profit_loss=0.91,
        )
        _result(
            db,
            prediction_id=loss_prediction.id,
            result="LOSS",
            profit_loss=-1.0,
        )
        _result(
            db,
            prediction_id=push_prediction.id,
            result="PUSH",
            profit_loss=0.0,
        )

        db.commit()

        performance = V1ReadService().get_performance(db=db)
        data = _dump(performance)

        assert data["wins"] == 1
        assert data["losses"] == 1
        assert data["pushes"] == 1

        # PUSH does not enter the denominator:
        # 1 WIN / (1 WIN + 1 LOSS) = 50%.
        assert data["accuracy"] == pytest.approx(50.0)

        assert data["profit_loss"] == pytest.approx(-0.09)

    finally:
        db.close()