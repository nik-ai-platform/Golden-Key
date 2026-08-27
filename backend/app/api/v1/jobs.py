from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.tasks.daily_job import DailyJob

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)

job = DailyJob()


@router.post("/daily")
def run_daily(
    db: Session = Depends(get_db),
):

    return job.execute(db)