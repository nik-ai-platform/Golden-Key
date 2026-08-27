from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.auth.dependencies import require_analyst, require_viewer
from app.database.session import get_db
from app.schemas.team_intelligence import TeamIntelligence

from app.schemas.team import (
    TeamCreate,
    TeamResponse
)

from app.services.team_intelligence_service import (
    TeamIntelligenceService
)
from app.services import team_service


router = APIRouter(
    prefix="/teams",
    tags=["Teams"],
    dependencies=[Depends(require_viewer)],
)


@router.post("/", response_model=TeamResponse)
def create_team(
    team: TeamCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_analyst),
):
    return team_service.create_team(db, team)


@router.get("/", response_model=list[TeamResponse])
def get_teams(
    db: Session = Depends(get_db)
):
    return team_service.get_teams(db)


@router.get(
    "/{team_id}/intelligence",
    response_model=TeamIntelligence
)
def get_team_intelligence(
    team_id: int,
    _current_user=Depends(require_viewer),
    db: Session = Depends(get_db)
):
    service = TeamIntelligenceService()

    return service.build_profile(
        db,
        team_id
    )


@router.get("/{team_id}/intelligence/detail")
def get_team_intelligence_detail(
    team_id: int,
    _current_user=Depends(require_viewer),
    db: Session = Depends(get_db),
):
    service = TeamIntelligenceService()
    return service.get_team_intelligence(db, team_id)
