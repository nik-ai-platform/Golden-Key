from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging

from app.api.v1 import teams
from app.api.v1 import games
from app.api.v1 import live
from app.api.v1 import imports
from app.api.v1 import odds
from app.api.v1 import predictions


setup_logging()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION
)


app.include_router(
    teams.router,
    prefix="/api/v1"
)

app.include_router(
    games.router,
    prefix="/api/v1"
)

app.include_router(
    live.router,
    prefix="/api/v1"
)

app.include_router(
    imports.router,
    prefix="/api/v1"
)

app.include_router(
    odds.router,
    prefix="/api/v1"
)

app.include_router(
    predictions.router,
    prefix="/api/v1"
)


@app.get("/health")
def health_check():

    return {
        "status": "Nik AI is online",
        "version": settings.VERSION
    }
