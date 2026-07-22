from sqlalchemy.orm import Session

from app.models.analytics_feature import AnalyticsFeature


def get_by_game(
    db: Session,
    game_id: int
):
    return (
        db.query(AnalyticsFeature)
        .filter(
            AnalyticsFeature.game_id == game_id
        )
        .first()
    )


def save(
    db: Session,
    analytics: AnalyticsFeature
):
    db.add(analytics)
    db.commit()
    db.refresh(analytics)
    return analytics
