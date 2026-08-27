from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"
    __table_args__ = (
        UniqueConstraint("prediction_id", name="uq_prediction_outcomes_prediction_id"),
        Index("ix_prediction_outcomes_created_at", "created_at"),
        Index("ix_prediction_outcomes_game_id", "game_id"),
    )

    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey("nik_scores.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    predicted_winner = Column(String, nullable=False)
    actual_winner = Column(String, nullable=False)
    predicted_confidence = Column(Float, nullable=False)
    prediction_correct = Column(Boolean, nullable=False)
    point_spread_error = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    prediction = relationship("NikScore", back_populates="outcomes")
    game = relationship("Game", back_populates="outcomes")

    @property
    def correct(self):
        return self.prediction_correct

    @property
    def confidence(self):
        return self.predicted_confidence
