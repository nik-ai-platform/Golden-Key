from app.models.analytics_feature import AnalyticsFeature
import logging


logger = logging.getLogger(__name__)


class FeatureGenerator:

    def generate_features(self):
        logger.info("FeatureGenerator.generate_features skipped: no job context provided.")
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
