from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.base import Base


class Parlay(Base):

    __tablename__ = "parlays"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, nullable=True)

    legs = Column(String, nullable=True)

    total_odds = Column(Float, nullable=True)

    probability = Column(Float, nullable=True)

    value_score = Column(Integer, nullable=True)

    risk_score = Column(Integer, nullable=True)

    stake = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
