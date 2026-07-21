from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.schemas.team import (
    TeamCreate,
    TeamResponse
)

from app.services import team_service


router = APIRouter(
    prefix="/teams",
    tags=["Teams"]
)


@router.post("/", response_model=TeamResponse)
def create_team(
    team: TeamCreate,
    db: Session = Depends(get_db)
):
    return team_service.create_team(db, team)


@router.get("/", response_model=list[TeamResponse])
def get_teams(
    db: Session = Depends(get_db)
):
    return team_service.get_teams(db)
