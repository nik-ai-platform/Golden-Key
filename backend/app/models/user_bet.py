from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.base import Base


class UserBet(Base):
    __tablename__ = "user_bets"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, nullable=False)
    game_id = Column(Integer, nullable=True)
    sport = Column(String, nullable=True)
    market = Column(String, nullable=True)
    selection = Column(String, nullable=True)
    odds = Column(Float, nullable=True)
    stake = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    expected_value = Column(Float, nullable=True)
    status = Column(String, nullable=True)
    result = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
