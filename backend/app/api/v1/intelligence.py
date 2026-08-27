from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.prediction_engine import PredictionEngine

router = APIRouter(
    prefix="/intelligence",
    tags=["Intelligence"],
)

engine = PredictionEngine()


@router.post("/analyze/{game_id}")
def analyze_game(
    game_id: int,
    db: Session = Depends(get_db),
):
    return engine.analyze_game(
        db,
        game_id,
    )
