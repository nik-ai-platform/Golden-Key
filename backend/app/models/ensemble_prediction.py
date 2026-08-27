from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.base import Base


class EnsemblePrediction(Base):

    __tablename__ = "ensemble_predictions"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, nullable=True)

    model_outputs = Column(String, nullable=True)

    final_prediction = Column(String, nullable=True)

    ensemble_score = Column(Integer, nullable=True)

    confidence = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
