from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.base import Base


class PredictionHistory(Base):

    __tablename__ = "prediction_history"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, nullable=True)

    model_version = Column(String, nullable=True)

    prediction = Column(String, nullable=True)

    confidence = Column(Integer, nullable=True)

    spread_prediction = Column(String, nullable=True)

    market_line = Column(String, nullable=True)

    recommended_bet = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    result_status = Column(String, nullable=True)
