from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, JSON

from app.database.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    risk_level = Column(String, nullable=True)
    preferred_sports = Column(JSON, nullable=True)
    preferred_markets = Column(JSON, nullable=True)
    betting_style = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
