from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import engine
from app.services.system_health_service import SystemHealthService


router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


@router.get("")
def health_check():
    return {"status": "healthy"}


@router.get("/ready")
def ready_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"},
        )

    return {
        "status": "healthy",
        "database": "connected",
    }


@router.get("/system")
def system_health():
    return SystemHealthService().check()
