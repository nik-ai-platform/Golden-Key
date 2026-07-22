from fastapi import APIRouter, HTTPException

from app.services import live_data_service


router = APIRouter(
    prefix="/live",
    tags=["Live Data"]
)


@router.get("/{sport}")
def get_live_data(
    sport: str
):
    try:
        return live_data_service.get_live_odds(sport)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch live data: {exc}"
        )
