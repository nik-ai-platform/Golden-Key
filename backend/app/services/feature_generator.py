from app.models.analytics_feature import AnalyticsFeature
from app.services.monitoring_service import MonitoringService


class FeatureGenerator:

    def __init__(
        self,
        monitor=None,
    ):
        self.monitor = monitor or MonitoringService()

    def generate_features(self):
        self.monitor.log_scheduler(
            "Feature generation skipped",
            reason="no_job_context"
        )
        return []

    def generate(
        self,
        game,
        latest_odds
    ) -> AnalyticsFeature:

        return AnalyticsFeature(
            game_id=game.id,

            home_rest_days=0,
            away_rest_days=0,

            line_movement=0.0,

            implied_home_probability=0.0,
            implied_away_probability=0.0,

            favorite_is_home=True,

            home_back_to_back=False,
            away_back_to_back=False
        )
