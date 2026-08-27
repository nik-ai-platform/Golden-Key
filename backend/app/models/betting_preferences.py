from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Boolean, Float

from app.database.base import Base


class BettingPreferences(Base):
    __tablename__ = "betting_preferences"

    id = Column(Integer, primary_key=True)
    favorite_bet_types = Column(String, nullable=True)
    minimum_confidence = Column(Integer, nullable=True)
    minimum_edge = Column(Float, nullable=True)
    max_parlay_legs = Column(Integer, nullable=True)
    avoid_high_variance = Column(Boolean, nullable=True)
    preferred_odds_range = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
