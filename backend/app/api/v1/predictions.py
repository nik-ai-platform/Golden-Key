from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_analyst
from app.database.session import get_db
from app.models.prediction_record import Prediction
from app.models.prediction_snapshot import PredictionSnapshot
from app.schemas.feature_importance import PredictionExplanation
from app.schemas.prediction import PredictionCreate, PredictionResponse
from app.repositories import game_repository
from app.services.cache_service import cache_service
from app.services.feature_importance_service import FeatureImportanceService
from app.services.prediction_evaluation_service import (
    PredictionEvaluationService
)
from app.services.prediction_service import create_prediction
from app.services.prediction_service import get_predictions


router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
    dependencies=[Depends(require_analyst)],
)


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
    selection = prediction.selection
    if prediction.market == "spread" and selection != "PASS":
        display_selection = f"{selection} {prediction.line_value:+g}"
    elif prediction.market == "moneyline" and selection != "PASS":
        team = game.home_team if selection == "HOME" else game.away_team
        display_selection = f"{team.name} ML"
    elif prediction.market == "total" and selection != "PASS":
        display_selection = f"{selection} {prediction.line_value:g}"
    else:
        display_selection = selection

    return {
        "prediction_id": prediction.id,
        "game_id": game.id,
        "sport": game.sport,
        "game_date": game.game_date.isoformat(),
        "home_team": game.home_team.name,
        "away_team": game.away_team.name,
        "market": prediction.market,
        "selection": selection,
        "display_selection": display_selection,
        "line_value": prediction.line_value,
        "american_odds": prediction.american_odds,
        "model_version": prediction.model_version,
        "npi_score": prediction.npi_score,
        "confidence_score": prediction.confidence_score,
        "simulation_probability": prediction.simulation_probability,
        "projected_edge": prediction.projected_edge,
        "risk_level": prediction.risk_level,
        "reasoning": prediction.reasoning,
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

    predictions = (
        db.query(Prediction)
        .filter(Prediction.game_id.in_(game_ids))
        .order_by(Prediction.id.desc())
        .all()
        if game_ids
        else []
    )
    latest_by_game_market = {}
    for prediction in predictions:
        latest_by_game_market.setdefault(
            (prediction.game_id, prediction.market),
            prediction,
        )
    games_by_id = {game.id: game for game in games}
    rows = [
        _prediction_payload(games_by_id[prediction.game_id], prediction)
        for prediction in latest_by_game_market.values()
        if prediction.game_id in games_by_id
    ]

    if winner:
        winner_lower = winner.lower()
        rows = [
            row
            for row in rows
            if winner_lower in row["display_selection"].lower()
        ]

    if min_confidence is not None:
        rows = [
            row
            for row in rows
            if (row["confidence_score"] or 0) >= min_confidence
        ]

    reverse = sort_order.lower() != "asc"
    sort_fields = {
        "confidence": "confidence_score",
        "confidence_score": "confidence_score",
        "nik_power_index": "npi_score",
        "npi_score": "npi_score",
        "game_date": "game_date",
        "market": "market",
        "model_version": "model_version",
        "winner": "display_selection",
        "selection": "display_selection",
    }
    key = sort_fields.get(sort_by, "confidence_score")
    rows.sort(key=lambda row: row[key] or 0, reverse=reverse)

    return rows


@router.get("/{game_id}")
def get_prediction(
    game_id: int,
    db: Session = Depends(get_db)
):
    cache_key = f"predictions:game:{game_id}:markets:v2"
    cached = cache_service.get(cache_key)
    if cached is not None:
        return cached

    game = game_repository.get_game_with_teams(db, game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    predictions = (
        db.query(Prediction)
        .filter(Prediction.game_id == game_id)
        .order_by(Prediction.id.desc())
        .all()
    )

    if not predictions:
        raise HTTPException(
            status_code=404,
            detail="Predictions not found"
        )

    latest_by_market = {}
    for prediction in predictions:
        latest_by_market.setdefault(prediction.market, prediction)
    payload = [
        _prediction_payload(game, latest_by_market[market])
        for market in ("spread", "moneyline", "total")
        if market in latest_by_market
    ]
    cache_service.set(cache_key, payload, ttl_seconds=30)
    return payload


@router.get("/{prediction_id}/explanation", response_model=PredictionExplanation)
def get_prediction_explanation(
    prediction_id: int,
    db: Session = Depends(get_db),
):
    prediction = (
        db.query(Prediction)
        .filter(Prediction.id == prediction_id)
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

    winner_features = snapshot.home_features or {} if snapshot else {}

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