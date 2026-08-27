from sqlalchemy.orm import Session

from app.models.backtest_result import BacktestResult
from app.services.cache_service import cache_service
from app.services.analytics_facade import (
    AnalyticsFacade
)


class DashboardService:

    def __init__(
        self,
        analytics_facade=None,
    ):

        self.facade = (
            analytics_facade or AnalyticsFacade()
        )

    def get_dashboard(
        self,
        db: Session,
        team_id: int | None = None,
    ):
        team_cache_key = team_id if team_id is not None else "all"
        cache_key = f"dashboard:response:{team_cache_key}"
        return cache_service.get_or_set(
            cache_key,
            lambda: self._build_dashboard(db, team_id),
            ttl_seconds=30,
        )

    def _build_dashboard(
        self,
        db: Session,
        team_id: int | None = None,
    ):
        response = self.facade.get_dashboard_data(db, team_id)
        response["model_lab"] = self._model_lab_summary(db)
        return response


    def get_team_intelligence_summary(
        self,
        db: Session,
        team_id: int
    ):
        return self.facade.get_team_intelligence_summary(
            db,
            team_id
        )


    def get_dashboard_bundle(
        self,
        db: Session,
        team_id: int | None = None,
        sport: str | None = None,
        version: str | None = None,
    ):
        return self.facade.get_dashboard_bundle(
            db,
            team_id=team_id,
            sport=sport,
            version=version,
        )

    def _model_lab_summary(self, db: Session):
        if not hasattr(db, "query"):
            return None

        rows = (
            db.query(BacktestResult)
            .order_by(BacktestResult.created_at.desc(), BacktestResult.id.desc())
            .limit(2)
            .all()
        )

        if not rows:
            return None

        current = rows[0]
        candidate = rows[1] if len(rows) > 1 else None

        return {
            "current": {
                "model_version": current.model_version,
                "roi": round(float(current.roi or 0.0), 2),
                "accuracy": round(float(current.accuracy or 0.0), 2),
            },
            "candidate": (
                {
                    "model_version": candidate.model_version,
                    "roi": round(float(candidate.roi or 0.0), 2),
                    "accuracy": round(float(candidate.accuracy or 0.0), 2),
                }
                if candidate is not None
                else None
            ),
            "status": (
                "ready_for_review"
                if candidate is not None and float(candidate.roi or 0.0) >= float(current.roi or 0.0)
                else "monitoring"
            ),
        }
