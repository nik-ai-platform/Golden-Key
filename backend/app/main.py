from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from time import perf_counter

from app.core.api_exceptions import APIException
from app.core.config import settings
from app.core.security_middleware import security_middleware
from app.core.logging_config import (
    setup_logging
)
from app.database.session import engine
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.system_health_service import SystemHealthService
from app.services.performance_metrics_service import performance_metrics

from app.api.v1 import teams
from app.api.v1 import games
from app.api.v1 import live
from app.api.v1 import imports
from app.api.v1 import odds
from app.api.v1 import predictions
from app.api.v1 import prediction_outcomes
from app.api.v1 import models
from app.api.v1 import backtests
from app.api.v1 import market
from app.api.v1 import bets
from app.api.v1 import bankroll
from app.api.v1 import parlays
from app.api.v1 import analyst
from app.api.v1 import features
from app.api.v1 import experiments
from app.api.v1 import ensemble
from app.api.v1 import performance
from app.api.v1 import prediction_history
from app.api.v1 import personalization
from app.api.v1 import strategies
from app.api.v1 import coach
from app.api.v1 import portfolio
from app.api.v1 import sports
from app.api.v1 import commercial
from app.api.v1 import assistant
from app.api.v1 import profile_intelligence
from app.api.v1 import community
from app.api.v1 import research_agent
from app.api.v1 import simulation
from app.api.v1 import enterprise
from app.api.v1 import learning
from app.api.v1 import auth
from app.api.v1 import users
from app.api.v1 import subscriptions
from app.api.v1 import premium
from app.api.v1 import results
from app.api.v1 import model
from app.api.v1 import model_promotion
from app.api.v1 import model_runtime
from app.api.v1 import model_bootstrap
from app.api.v1 import npi_weights
from app.api.v1 import system_integration
from app.api.v1 import settlement
from app.api.v1 import product
from app.api.v1 import version
from app.api.v1 import readiness
from app.api.v1 import agent
from app.api.v1 import agents
from app.api.v1 import discovery
from app.api.v1 import intelligence
from app.api.v1 import pipeline
from app.api.v1 import jobs
from app.api.v1 import onboarding
from app.api.routes import analytics
from app.api.routes import dashboard
from app.api.routes import health


setup_logging()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(SecurityHeadersMiddleware)


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
    prediction_outcomes.router,
    prefix="/api/v1"
)

app.include_router(
    predictions.router,
    prefix="/api/v1"
)

app.include_router(
    models.router,
    prefix="/api/v1"
)

app.include_router(
    backtests.router,
    prefix="/api/v1"
)

app.include_router(
    market.router,
    prefix="/api/v1"
)

app.include_router(
    bets.router,
    prefix="/api/v1"
)

app.include_router(
    bankroll.router,
    prefix="/api/v1"
)

app.include_router(
    parlays.router,
    prefix="/api/v1"
)

app.include_router(
    analyst.router,
    prefix="/api/v1"
)

app.include_router(
    features.router,
    prefix="/api/v1"
)

app.include_router(
    experiments.router,
    prefix="/api/v1"
)

app.include_router(
    ensemble.router,
    prefix="/api/v1"
)

app.include_router(
    performance.router,
    prefix="/api/v1"
)

app.include_router(
    prediction_history.router,
    prefix="/api/v1"
)

app.include_router(
    personalization.router,
    prefix="/api/v1"
)

app.include_router(
    strategies.router,
    prefix="/api/v1"
)

app.include_router(
    coach.router,
    prefix="/api/v1"
)

app.include_router(
    portfolio.router,
    prefix="/api/v1"
)

app.include_router(
    sports.router,
    prefix="/api/v1"
)

app.include_router(
    commercial.router,
    prefix="/api/v1"
)

app.include_router(
    assistant.router,
    prefix="/api/v1"
)

app.include_router(
    profile_intelligence.router,
    prefix="/api/v1"
)

app.include_router(
    community.router,
    prefix="/api/v1"
)

app.include_router(
    research_agent.router,
    prefix="/api/v1"
)

app.include_router(
    simulation.router,
    prefix="/api/v1"
)

app.include_router(
    learning.router,
    prefix="/api/v1"
)

app.include_router(
    agent.router,
    prefix="/api/v1"
)

app.include_router(
    agents.router,
    prefix="/api/v1"
)

app.include_router(
    discovery.router,
    prefix="/api/v1"
)

app.include_router(
    intelligence.router,
    prefix="/api/v1"
)

app.include_router(
    pipeline.router,
    prefix="/api/v1"
)

app.include_router(
    jobs.router,
    prefix="/api/v1"
)

app.include_router(
    onboarding.router,
    prefix="/api/v1"
)

app.include_router(
    enterprise.router,
    prefix="/api/v1"
)

app.include_router(
    auth.router,
    prefix="/api/v1"
)

app.include_router(
    users.router,
    prefix="/api/v1"
)

app.include_router(
    results.router,
    prefix="/api/v1"
)

app.include_router(
    model.router,
    prefix="/api/v1"
)

app.include_router(
    model_promotion.router,
    prefix="/api/v1"
)

app.include_router(
    model_runtime.router,
    prefix="/api/v1"
)

app.include_router(
    model_bootstrap.router,
    prefix="/api/v1"
)

app.include_router(
    npi_weights.router,
    prefix="/api/v1"
)

app.include_router(
    system_integration.router,
    prefix="/api/v1"
)

app.include_router(
    settlement.router,
    prefix="/api/v1"
)

app.include_router(
    product.router,
    prefix="/api/v1"
)

app.include_router(
    version.router,
    prefix="/api/v1"
)

app.include_router(
    readiness.router,
    prefix="/api/v1"
)

app.include_router(
    subscriptions.router,
    prefix="/api/v1"
)

app.include_router(
    premium.router,
    prefix="/api/v1"
)

app.include_router(
    analytics.router,
    prefix="/api/v1"
)

app.include_router(
    dashboard.router,
    prefix="/api/v1"
)

app.include_router(
    health.router,
    prefix="/api/v1"
)


@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    started_at = perf_counter()
    protected = await security_middleware.guard(request, call_next)
    response = protected
    duration_ms = round((perf_counter() - started_at) * 1000, 2)

    performance_metrics.record_api_request(
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )

    return response


@app.exception_handler(APIException)
async def api_exception_handler(
    request: Request,
    exc: APIException
):

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


@app.get("/ready")
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


@app.get("/health/system")
def system_health_check():
    return SystemHealthService().check()
