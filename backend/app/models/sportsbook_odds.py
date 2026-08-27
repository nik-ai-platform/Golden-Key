from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Float

from app.database.base import Base


class SportsbookOdds(Base):
    __tablename__ = "sportsbook_odds"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False)
    sportsbook = Column(String, nullable=False)
    market_type = Column(String, nullable=True)
    spread = Column(String, nullable=True)
    moneyline = Column(String, nullable=True)
    total = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
