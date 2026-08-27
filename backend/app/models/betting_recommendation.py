from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.base import Base


class BettingRecommendation(Base):

    __tablename__ = "betting_recommendations"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, nullable=True)

    market_type = Column(String, nullable=True)

    selection = Column(String, nullable=True)

    confidence = Column(Integer, nullable=True)

    value_score = Column(Integer, nullable=True)

    risk_score = Column(Integer, nullable=True)

    quality_score = Column(Integer, nullable=True)

    recommendation = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
