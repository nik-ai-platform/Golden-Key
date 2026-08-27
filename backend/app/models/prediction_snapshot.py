from sqlalchemy import Column, ForeignKey, Integer, String, Float, JSON
from sqlalchemy import Index

from app.database.base import Base


class PredictionSnapshot(Base):

    __tablename__ = "prediction_snapshots"

    id = Column(Integer, primary_key=True)

    game_id = Column(
        Integer,
        ForeignKey("games.id"),
        nullable=False
    )

    model_version = Column(String)

    prediction = Column(String)

    confidence = Column(Float)

    home_score = Column(Float)

    away_score = Column(Float)

    home_features = Column(JSON)

    away_features = Column(JSON)


Index(
    "idx_snapshot_game",
    PredictionSnapshot.game_id
)


Index(
    "idx_snapshot_model",
    PredictionSnapshot.model_version
)
