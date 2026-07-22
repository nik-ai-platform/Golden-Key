from sqlalchemy.orm import Session

from app.models.analytics_feature import AnalyticsFeature
from app.services.feature_engine import FeatureEngine


class AnalyticsService:

    def __init__(self):
        self.engine = FeatureEngine()

    def create_game_features(
        self,
        db: Session,
        game,
        odds
    ):

        existing = (
            db.query(AnalyticsFeature)
            .filter(
                AnalyticsFeature.game_id == game.id
            )
            .first()
        )

        if existing:
            return existing

        moneyline_features = (
            self.engine.calculate_moneyline_features(
                odds.moneyline_home,
                odds.moneyline_away
            )
        )

        analytics = AnalyticsFeature(

            game_id=game.id,

            implied_home_probability=
                moneyline_features[
                    "implied_home_probability"
                ],

            implied_away_probability=
                moneyline_features[
                    "implied_away_probability"
                ],

            favorite_is_home=
                moneyline_features[
                    "favorite_is_home"
                ],

            line_movement=None,

            home_rest_days=None,

            away_rest_days=None,

            home_back_to_back=None,

            away_back_to_back=None
        )

        db.add(analytics)
        db.commit()
        db.refresh(analytics)

        return analytics
