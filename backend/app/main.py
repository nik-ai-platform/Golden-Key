from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging


setup_logging()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION
)


@app.get("/health")
def health_check():

    return {
        "status": "Nik AI is online",
        "version": settings.VERSION
    }
