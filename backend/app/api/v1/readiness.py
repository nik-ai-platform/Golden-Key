from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db


router = APIRouter(
    prefix="/readiness",
    tags=["System"],
)


@router.get("")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from error

    return {
        "status": "ready",
        "database": "connected",
    }
