from fastapi import APIRouter, BackgroundTasks, Depends, Query

from sqlalchemy.orm import Session

from app.auth.dependencies import require_viewer
from app.database.session import SessionLocal
from app.database.session import get_db
from app.schemas.confidence_analytics import ConfidenceAnalytics
from app.schemas.historical_trends import (
    HistoricalTrendResponse,
    ModelTrendPoint,
    SportTrendPoint,
    TeamTrendResponse,
    TrendPoint,
)

from app.services.analytics.analytics_service import AnalyticsService
from app.services.analytics.backtest_service import BacktestService
from app.services.analytics.confidence_service import ConfidenceService
from app.services.cache_service import cache_service
from app.services.calibration_service import CalibrationService
from app.services.feature_importance_service import FeatureImportanceService
from app.services.historical_trend_service import HistoricalTrendService
from app.services.performance_engine import (
    PerformanceEngine
)
from app.services.performance_metrics_service import performance_metrics


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)

engine = PerformanceEngine()


def _run_backtest_background(limit: int):
    db = SessionLocal()
    try:
        BacktestService().run_backtest(db, limit=limit)
    finally:
        db.close()


@router.get("/accuracy")
def accuracy(
    db: Session = Depends(get_db),
    _current_user=Depends(require_viewer),
):

    analytics = AnalyticsService()
    confidence = ConfidenceService()

    return {
        "overall_accuracy": analytics.overall_accuracy(db),
        "sport_accuracy": analytics.sport_accuracy(db),
        "model_accuracy": analytics.model_accuracy(db),
        "confidence_accuracy": confidence.confidence_buckets(db),
        "dashboard_statistics": analytics.dashboard_statistics(db),
    }


@router.get(
    "/confidence",
    response_model=ConfidenceAnalytics,
)
def confidence_analytics(
    db: Session = Depends(get_db),
    _current_user=Depends(require_viewer),
):
    confidence = ConfidenceService()

    return cache_service.get_or_set(
        "analytics:confidence:distribution",
        lambda: confidence.get_confidence_distribution(db),
        ttl_seconds=90,
    )


@router.get("/calibration")
def calibration_analytics(
    db: Session = Depends(get_db),
    _current_user=Depends(require_viewer),
):
    calibration = CalibrationService()

    return cache_service.get_or_set(
        "analytics:calibration",
        lambda: calibration.calculate_calibration(db=db),
        ttl_seconds=120,
    )


@router.get("/feature-importance")
def feature_importance_analytics(
    db: Session = Depends(get_db),
    _current_user=Depends(require_viewer),
):
    feature_importance = FeatureImportanceService()

    return cache_service.get_or_set(
        "analytics:feature-importance",
        lambda: feature_importance.historical_importance(db),
        ttl_seconds=180,
    )


@router.get("/model-learning")
def model_learning_analytics(
    db: Session = Depends(get_db),
    _current_user=Depends(require_viewer),
):
    analytics = AnalyticsService()
    summary = cache_service.get_or_set(
        "analytics:model-learning-summary",
        lambda: analytics.dashboard_statistics(db),
        ttl_seconds=120,
    )

    return summary.get(
        "model_learning",
        {
            "current_model": "unknown",
            "training_samples": 0,
            "candidate_models": 0,
            "best_candidate": None,
        },
    )


@router.get("/performance")
def performance_analytics(
    db: Session = Depends(get_db)
):
    return engine.calculate_metrics(
        db
    )


@router.get("/runtime-performance")
def runtime_performance_analytics():
    return performance_metrics.snapshot()


@router.get("/trends/daily", response_model=list[TrendPoint])
def daily_trends(
    db: Session = Depends(get_db),
    _current_user=Depends(require_viewer),
):
    trends = HistoricalTrendService()

    return trends.daily_trends(db)


@router.get("/trends/weekly", response_model=list[TrendPoint])
def weekly_trends(
    db: Session = Depends(get_db),
    _current_user=Depends(require_viewer),
):
    trends = HistoricalTrendService()

    return trends.weekly_trends(db)


@router.get("/trends/monthly", response_model=list[TrendPoint])
def monthly_trends(
    db: Session = Depends(get_db),
    _current_user=Depends(require_viewer),
):
    trends = HistoricalTrendService()

    return trends.monthly_trends(db)


@router.get("/trends/team/{team_id}", response_model=TeamTrendResponse)
def team_trends(
    team_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(require_viewer),
):
    trends = HistoricalTrendService()

    return trends.team_trends(db, team_id)


@router.get("/trends/sport", response_model=list[SportTrendPoint])
def sport_trends(
    db: Session = Depends(get_db),
    sport: str | None = None,
    _current_user=Depends(require_viewer),
):
    trends = HistoricalTrendService()

    return trends.sport_trends(db, sport)


@router.get("/trends/model", response_model=list[ModelTrendPoint])
def model_trends(
    db: Session = Depends(get_db),
    version: str | None = None,
    _current_user=Depends(require_viewer),
):
    trends = HistoricalTrendService()

    return trends.model_trends(db, version)


@router.get("/backtesting")
def backtesting(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    limit: int = 100,
    async_run: bool = Query(default=False),
    _current_user=Depends(require_viewer),
):
    backtest = BacktestService()

    if async_run:
        background_tasks.add_task(_run_backtest_background, limit)
        return {
            "status": "accepted",
            "job": "backtesting",
            "limit": limit,
        }

    return backtest.run_backtest(db, limit=limit)
