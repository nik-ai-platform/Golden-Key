import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import ValidationError

from app.auth.dependencies import require_admin
from app.core.config import settings
from app.database.telemetry_session import TelemetryError
from app.schemas.worker_status import WorkerStatusResponse
from app.services.worker_status_service import WorkerStatusService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/operations", tags=["Operations"], dependencies=[Depends(require_admin)])


def status_service() -> WorkerStatusService:
    return WorkerStatusService(grace_seconds=settings.OPERATIONS_STARTUP_GRACE_SECONDS)


@router.get("/workers", response_model=WorkerStatusResponse)
def worker_status(response: Response, service: WorkerStatusService = Depends(status_service)) -> WorkerStatusResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return service.read()
    except TelemetryError as error:
        logger.warning("Worker status unavailable code=%s", error.code)
        raise HTTPException(
            status_code=503, detail="Worker telemetry storage is unavailable",
            headers={"Cache-Control": "no-store"},
        ) from None
    except ValidationError:
        logger.warning("Worker status unavailable code=invalid_evidence")
        raise HTTPException(
            status_code=503, detail="Worker telemetry storage is unavailable",
            headers={"Cache-Control": "no-store"},
        ) from None
