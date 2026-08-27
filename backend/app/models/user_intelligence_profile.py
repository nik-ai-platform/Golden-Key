from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, JSON

from app.database.base import Base


class UserIntelligenceProfile(Base):
    __tablename__ = "user_intelligence_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    risk_level = Column(String, nullable=False, default="moderate")
    preferred_sports = Column(JSON, nullable=True)
    preferred_bet_types = Column(JSON, nullable=True)
    average_stake = Column(Integer, nullable=True)
    favorite_markets = Column(JSON, nullable=True)
    confidence_threshold = Column(Integer, nullable=True, default=78)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
