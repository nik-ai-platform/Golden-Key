from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.prediction_service import PredictionService


router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"]
)


service = PredictionService()


@router.get("/{game_id}")
def get_prediction(
    game_id: int,
    db: Session = Depends(get_db)
):

    prediction = service.generate_prediction(
        db,
        game_id
    )

    if not prediction:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    return {
        "game_id": prediction.game_id,
        "home_score": prediction.home_score,
        "away_score": prediction.away_score,
        "confidence": prediction.confidence,
        "recommendation": prediction.recommendation
    }