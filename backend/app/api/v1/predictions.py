from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import require_analyst
from app.database.session import get_db
from app.models.nik_score import NikScore
from app.models.prediction_snapshot import PredictionSnapshot
from app.schemas.feature_importance import PredictionExplanation
from app.schemas.prediction import PredictionCreate, PredictionResponse
from app.repositories import game_repository
from app.services.cache_service import cache_service
from app.services.feature_importance_service import FeatureImportanceService
from app.services.prediction_evaluation_service import (
    PredictionEvaluationService
)
from app.services.prediction_service import PredictionService
from app.services.prediction_service import create_prediction
from app.services.prediction_service import get_predictions


router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
    dependencies=[Depends(require_analyst)],
)


service = PredictionService()
evaluation_service = PredictionEvaluationService()
importance_service = FeatureImportanceService()


class PredictionEvaluationRequest(BaseModel):
    actual_winner: str


@router.post("/", response_model=PredictionResponse)
def create_prediction_record(
    prediction: PredictionCreate,
    db: Session = Depends(get_db),
):
    if not game_repository.get_game_by_id(db, prediction.game_id):
        raise HTTPException(status_code=404, detail="Game not found")

    return create_prediction(
        db,
        prediction,
    )


@router.get("/stored", response_model=list[PredictionResponse])
def list_stored_predictions(
    db: Session = Depends(get_db),
):
    return get_predictions(db)


def _prediction_payload(game, prediction):
    return {
        "game_id": game.id,
        "game_date": game.game_date,
        "home_team": game.home_team.name,
        "away_team": game.away_team.name,
        "winner": prediction.recommendation,
        "confidence": prediction.confidence,
        "nik_power_index": round(max(prediction.home_score, prediction.away_score), 2),
        "home_npi": prediction.home_score,
        "away_npi": prediction.away_score,
        "model_version": prediction.model_version,
    }


def _prediction_payload_without_game(game_id: int, prediction):
    return {
        "game_id": game_id,
        "game_date": None,
        "home_team": "Unknown",
        "away_team": "Unknown",
        "winner": prediction.recommendation,
        "confidence": prediction.confidence,
        "nik_power_index": round(max(prediction.home_score, prediction.away_score), 2),
        "home_npi": prediction.home_score,
        "away_npi": prediction.away_score,
        "model_version": getattr(prediction, "model_version", "NPI-v1"),
    }


@router.get("")
def list_predictions(
    db: Session = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=200),
    winner: str | None = None,
    min_confidence: float | None = Query(default=None, ge=0, le=100),
    sort_by: str = Query(default="confidence"),
    sort_order: str = Query(default="desc"),
):
    games = game_repository.get_games_with_teams(db, limit=limit)
    game_ids = [game.id for game in games]

    latest_by_game_id: dict[int, NikScore] = {}
    if game_ids:
        latest_prediction_ids = (
            db.query(
                NikScore.game_id.label("game_id"),
                func.max(NikScore.id).label("prediction_id"),
            )
            .filter(NikScore.game_id.in_(game_ids))
            .group_by(NikScore.game_id)
            .subquery()
        )

        latest_predictions = (
            db.query(NikScore)
            .join(
                latest_prediction_ids,
                NikScore.id == latest_prediction_ids.c.prediction_id,
            )
            .all()
        )

        latest_by_game_id = {
            prediction.game_id: prediction
            for prediction in latest_predictions
        }

    team_ids = {
        game.home_team.id
        for game in games
    } | {
        game.away_team.id
        for game in games
    }

    recent_games_map = game_repository.get_recent_games_for_teams(
        db,
        list(team_ids),
        limit=10,
    )

    rows = []

    for game in games:
        latest = latest_by_game_id.get(game.id)

        prediction = latest or service.generate_prediction(
            db,
            game.id,
            preloaded_recent_games=recent_games_map,
        )
        if not prediction:
            continue

        rows.append(_prediction_payload(game, prediction))

    if winner:
        winner_lower = winner.lower()
        rows = [row for row in rows if winner_lower in row["winner"].lower()]

    if min_confidence is not None:
        rows = [row for row in rows if row["confidence"] >= min_confidence]

    reverse = sort_order.lower() != "asc"
    supported_sort = {"confidence", "nik_power_index", "game_date", "model_version", "winner"}
    key = sort_by if sort_by in supported_sort else "confidence"
    rows.sort(key=lambda row: row[key], reverse=reverse)

    return rows


@router.get("/{game_id}")
def get_prediction(
    game_id: int,
    db: Session = Depends(get_db)
):
    cache_key = f"predictions:game:{game_id}"
    cached = cache_service.get(cache_key)
    if cached is not None:
        return cached

    if not hasattr(db, "query"):
        prediction = service.generate_prediction(db, game_id)
        if not prediction:
            raise HTTPException(status_code=404, detail="Game not found")
        payload = _prediction_payload_without_game(game_id, prediction)
        cache_service.set(cache_key, payload, ttl_seconds=30)
        return payload

    game = game_repository.get_game_with_teams(db, game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    prediction = (
        db.query(NikScore)
        .filter(NikScore.game_id == game_id)
        .order_by(NikScore.id.desc())
        .first()
    )

    if prediction is None:
        prediction = service.generate_prediction(
            db,
            game_id
        )

    if not prediction:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    payload = _prediction_payload(game, prediction)
    cache_service.set(cache_key, payload, ttl_seconds=30)
    return payload


@router.get("/{prediction_id}/explanation", response_model=PredictionExplanation)
def get_prediction_explanation(
    prediction_id: int,
    db: Session = Depends(get_db),
):
    prediction = (
        db.query(NikScore)
        .filter(NikScore.id == prediction_id)
        .first()
    )

    if not prediction:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found",
        )

    snapshot = (
        db.query(PredictionSnapshot)
        .filter(PredictionSnapshot.game_id == prediction.game_id)
        .order_by(PredictionSnapshot.id.desc())
        .first()
    )

    winner_features = {}
    if snapshot:
        if float(prediction.home_score or 0.0) >= float(prediction.away_score or 0.0):
            winner_features = snapshot.home_features or {}
        else:
            winner_features = snapshot.away_features or {}

    return importance_service.explain_prediction(
        prediction,
        features=winner_features,
    )


@router.post(
    "/{prediction_id}/evaluate"
)
def evaluate_prediction(
    prediction_id: int,
    request: PredictionEvaluationRequest,
    db: Session = Depends(get_db)
):

    service = PredictionEvaluationService()

    result = service.evaluate_prediction(
        db,
        prediction_id,
        request.actual_winner
    )

    if not result:
        return {
            "error": "Prediction not found"
        }

    return {

        "prediction_id":
            result.prediction_id,

        "predicted_winner":
            result.predicted_winner,

        "actual_winner":
            result.actual_winner,

        "correct":
            result.correct,

        "accuracy":
            result.prediction_accuracy,

        "confidence":
            result.confidence
    }