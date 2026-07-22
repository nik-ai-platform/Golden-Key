from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.import_service import import_sport_games


router = APIRouter(
    prefix="/imports",
    tags=["Imports"]
)


@router.post("/{sport}")
def import_games(
    sport: str,
    db: Session = Depends(get_db)
):

    games = import_sport_games(
        db,
        sport.upper()
    )

    return {
        "imported_games": len(games)
    }
