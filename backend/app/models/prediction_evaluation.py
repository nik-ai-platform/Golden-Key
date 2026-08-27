from sqlalchemy import (
    Column,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    Index
)

from app.database.base import Base


class PredictionEvaluation(Base):

    __tablename__ = "prediction_evaluations"


    id = Column(
        Integer,
        primary_key=True
    )


    snapshot_id = Column(
        Integer,
        ForeignKey(
            "prediction_snapshots.id"
        ),
        nullable=False
    )


    correct = Column(
        Boolean
    )


    predicted_team = Column(
        Integer
    )


    actual_winner = Column(
        Integer
    )


    confidence = Column(
        Float
    )


Index(
    "idx_evaluation_snapshot",
    PredictionEvaluation.snapshot_id
)


Index(
    "idx_evaluation_correct",
    PredictionEvaluation.correct
)
