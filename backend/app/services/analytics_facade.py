from sqlalchemy.orm import Session
from time import perf_counter

from app.services.analytics.analytics_service import (
    AnalyticsService
)
from app.services.historical_trend_service import (
    HistoricalTrendService
)
from app.services.monitoring_service import (
    MonitoringService
)
from app.services.prediction_metrics_service import (
    PredictionMetricsService
)
from app.services.team_intelligence_service import (
    TeamIntelligenceService
)


class AnalyticsFacade:
    """
    Orchestrates dashboard-facing analytics and team intelligence flows.
    """


    def __init__(
        self,
        analytics_service=None,
        team_intelligence_service=None,
        prediction_metrics_service=None,
        monitoring_service=None,
        historical_trend_service=None,
    ):
        self.analytics = (
            analytics_service or AnalyticsService()
        )
        self.team_intelligence = (
            team_intelligence_service or TeamIntelligenceService()
        )
        self.metrics = (
            prediction_metrics_service or PredictionMetricsService(
                analytics_service=self.analytics,
            )
        )
        self.monitor = (
            monitoring_service or MonitoringService()
        )
        self.trends = (
            historical_trend_service or HistoricalTrendService()
        )


    def get_dashboard_data(
        self,
        db: Session,
        team_id: int | None = None,
    ):
        started_at = perf_counter()

        summary = self.analytics.dashboard_statistics(db)
        summary_ms = round((perf_counter() - started_at) * 1000, 2)

        recent_predictions = summary.get("recent_predictions", [])
        model_accuracy = summary.get("model_accuracy")
        if model_accuracy is None:
            model_accuracy = self.metrics.accuracy_by_model_version(db)
        model_accuracy_ms = round((perf_counter() - started_at) * 1000, 2)
        overall_accuracy = summary.get("overall_accuracy")
        if overall_accuracy is None:
            overall_accuracy = self.metrics.overall_accuracy(db)
        overall_accuracy_ms = round((perf_counter() - started_at) * 1000, 2)

        response = {
            "system_health": "healthy",
            "overall_accuracy": overall_accuracy,
            "total_predictions": len(recent_predictions),
            "recent_predictions": recent_predictions,
            "top_teams": [],
            "model_versions": [
                {
                    "model": version,
                    **metrics,
                }
                for version, metrics in model_accuracy.items()
            ],
        }

        if team_id is not None:
            profile = self.team_intelligence.build_profile(
                db,
                team_id
            )

            response["top_teams"].append(
                {
                    "team_id": profile.team_id,
                    "team_name": profile.team_name,
                    "momentum": profile.momentum,
                    "strength_rating": profile.strength_rating,
                }
            )

        self.monitor.log_scheduler(
            "Dashboard assembled",
            team_id=team_id,
            total_predictions=response["total_predictions"],
            total_ms=round((perf_counter() - started_at) * 1000, 2),
            summary_ms=summary_ms,
            model_accuracy_ms=model_accuracy_ms,
            overall_accuracy_ms=overall_accuracy_ms,
        )

        return response


    def get_dashboard_bundle(
        self,
        db: Session,
        team_id: int | None = None,
        sport: str | None = None,
        version: str | None = None,
    ):
        return {
            "dashboard": self.get_dashboard_data(db, team_id=team_id),
            "trends": self.get_historical_trends(
                db,
                team_id=team_id,
                sport=sport,
                version=version,
            ),
        }


    def get_team_intelligence_summary(
        self,
        db: Session,
        team_id: int
    ):
        return self.team_intelligence.get_dashboard_summary(
            db,
            team_id
        )


    def get_historical_trends(
        self,
        db: Session,
        team_id: int | None = None,
        sport: str | None = None,
        version: str | None = None,
    ):
        return {
            "daily": self.trends.daily_trends(db),
            "weekly": self.trends.weekly_trends(db),
            "monthly": self.trends.monthly_trends(db),
            "team": (
                self.trends.team_trends(db, team_id)
                if team_id is not None
                else None
            ),
            "sport": (
                self.trends.sport_trends(db, sport)
                if sport is not None
                else []
            ),
            "model": (
                self.trends.model_trends(db, version)
                if version is not None
                else []
            ),
        }