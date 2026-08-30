from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import users as users_router
from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthUser
from app.core.roles import UserRole
from app.database.base import Base
from app.database.session import get_db
from app.models.game import Game
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.user import User
from app.models.user_prediction import UserPrediction
from app.services.v1_read_service import V1ReadService


def _setup():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()

    owner = User(
        username="admin",
        email="admin@example.com",
        hashed_password="unused",
        role=UserRole.ADMIN,
        is_active=True,
    )
    other = User(
        username="other",
        email="other@example.com",
        hashed_password="unused",
        role=UserRole.VIEWER,
        is_active=True,
    )
    home = Team(name="Home", league="NFL", sport="NFL")
    away = Team(name="Away", league="NFL", sport="NFL")
    db.add_all([owner, other, home, away])
    db.flush()
    game = Game(
        sport="NFL",
        league="NFL",
        game_date=datetime.now(timezone.utc),
        home_team_id=home.id,
        away_team_id=away.id,
    )
    db.add(game)
    db.flush()
    predictions = []
    for market in ("spread", "moneyline", "total"):
        prediction = Prediction(
            game_id=game.id,
            market=market,
            selection="HOME",
            line_value=-3.5 if market == "spread" else None,
            american_odds=-110,
            npi_score=150.0,
            confidence_score=80.0,
            model_version="NPI-4.0",
        )
        db.add(prediction)
        db.flush()
        predictions.append(prediction)
    db.commit()

    app = FastAPI()
    app.include_router(users_router.router, prefix="/api/v1")

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id=0,
        username="admin",
        email="admin@example.com",
        role="admin",
        is_active=True,
        email_verified=False,
    )
    return TestClient(app), db, owner, other, game, predictions


def test_authenticated_user_removes_own_unsettled_saved_pick():
    client, db, owner, _, game, predictions = _setup()
    prediction = predictions[0]
    db.add(UserPrediction(user_id=owner.id, prediction_id=prediction.id))
    db.commit()

    response = client.delete(
        f"/api/v1/users/saved-predictions/{prediction.id}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "removed": True,
        "prediction_id": prediction.id,
    }
    assert db.get(UserPrediction, 1) is None
    assert db.get(Prediction, prediction.id) is not None
    assert db.get(Game, game.id) is not None
    db.close()


def test_remove_is_user_scoped_and_unsaved_request_is_idempotent():
    client, db, _, other, _, predictions = _setup()
    prediction = predictions[1]
    saved = UserPrediction(user_id=other.id, prediction_id=prediction.id)
    db.add(saved)
    db.commit()
    saved_id = saved.id

    response = client.delete(
        f"/api/v1/users/saved-predictions/{prediction.id}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "removed": False,
        "prediction_id": prediction.id,
    }
    assert db.get(UserPrediction, saved_id) is not None
    db.close()


def test_removing_settled_pick_preserves_result_and_performance():
    client, db, owner, _, _, predictions = _setup()
    prediction = predictions[2]
    saved = UserPrediction(user_id=owner.id, prediction_id=prediction.id)
    result = PredictionResult(
        prediction_id=prediction.id,
        actual_result="HOME",
        predicted_result="HOME",
        outcome="WIN",
        profit_loss=0.91,
    )
    db.add_all([saved, result])
    db.commit()
    result_id = result.id
    before = V1ReadService().get_performance(db=db)

    response = client.delete(
        f"/api/v1/users/saved-predictions/{prediction.id}"
    )

    assert response.json()["removed"] is True
    assert db.get(PredictionResult, result_id) is not None
    assert V1ReadService().get_performance(db=db) == before
    db.close()