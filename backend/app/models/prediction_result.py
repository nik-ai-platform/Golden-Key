from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)

from sqlalchemy.sql import func

from app.database.base import Base


class PredictionResult(Base):

    __tablename__ = "prediction_results"
    __table_args__ = (
        UniqueConstraint(
            "prediction_id",
            name="uq_prediction_result_prediction",
        ),
    )

    id = Column(
        Integer,
        primary_key=True
    )
    prediction_id = Column(
        Integer,
        ForeignKey(
            "predictions.id"
        ),
        nullable=False
    )

    actual_result = Column(
        String,
        nullable=False
    )

    predicted_result = Column(
        String,
        nullable=False
    )

    outcome = Column(
        String,
        nullable=False
    )

    profit_loss = Column(
        Float,
        default=0
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )
