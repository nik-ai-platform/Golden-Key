from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    UniqueConstraint
)

from sqlalchemy.sql import func

from app.database.base import Base


class UserPrediction(Base):

    __tablename__ = "user_predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "prediction_id", name="uq_user_predictions_user_prediction"),
    )

    id = Column(
        Integer,
        primary_key=True
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id"
        ),
        nullable=False
    )

    prediction_id = Column(
        Integer,
        ForeignKey(
            "predictions.id"
        ),
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )