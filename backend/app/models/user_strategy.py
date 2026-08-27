from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, JSON

from app.database.base import Base


class UserStrategy(Base):
    __tablename__ = "user_strategies"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    strategy_name = Column(String, nullable=False)
    sport = Column(String, nullable=True)
    market_type = Column(String, nullable=True)
    rules = Column(JSON, nullable=True)
    starting_bankroll = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
