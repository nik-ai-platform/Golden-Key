from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.auth.dependencies import require_analyst
from app.database.session import get_db
from app.services.import_service import import_sport_games


router = APIRouter(
    prefix="/imports",
    tags=["Imports"],
    dependencies=[Depends(require_analyst)],
)


@router.post("/{sport}")
def import_games(
    sport: str,
    db: Session = Depends(get_db)
):

    games = import_sport_games(
        db,
        sport.lower()
    )

    return {
        "imported_games": len(games)
    }
