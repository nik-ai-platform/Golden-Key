from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging

from app.api.v1 import teams


setup_logging()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION
)


app.include_router(
    teams.router,
    prefix="/api/v1"
)


@app.get("/health")
def health_check():

    return {
        "status": "Nik AI is online",
        "version": settings.VERSION
    }
