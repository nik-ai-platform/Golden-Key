from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_viewer
from app.database.session import get_db
from app.schemas.dashboard import DashboardResponse
from app.schemas.team_intelligence import TeamIntelligenceSummary

from app.services.dashboard_service import DashboardService


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_viewer)],
)


@router.get("", response_model=DashboardResponse)
def dashboard(
    db: Session = Depends(get_db),
    team_id: int | None = None,
):

    service = DashboardService()

    return service.get_dashboard(
        db,
        team_id
    )


@router.get("/team/{team_id}", response_model=TeamIntelligenceSummary)
def team_dashboard(
    team_id: int,
    db: Session = Depends(get_db)
):

    service = DashboardService()

    return service.get_team_intelligence_summary(
        db,
        team_id
    )
