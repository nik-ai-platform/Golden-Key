from sqlalchemy.orm import Session

from app.services.analytics.analytics_service import (
    AnalyticsService
)
from app.services.analytics.confidence_service import (
    ConfidenceService
)


class PredictionMetricsService:
    """Compatibility wrapper for analytics metrics methods."""


    def __init__(
        self,
        analytics_service=None,
        confidence_service=None,
    ):
        self.analytics = (
            analytics_service or AnalyticsService()
        )
        self.confidence = (
            confidence_service or ConfidenceService()
        )


    def overall_accuracy(
        self,
        db: Session
    ):
        return self.analytics.calculate_accuracy(db=db)


    def accuracy_by_model_version(
        self,
        db: Session
    ):
        return self.analytics.model_accuracy(db)


    def accuracy_by_confidence(
        self,
        db: Session
    ):
        return self.confidence.confidence_buckets(db)
