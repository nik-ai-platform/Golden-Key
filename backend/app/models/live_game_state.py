from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Float

from app.database.base import Base


class LiveGameState(Base):
    __tablename__ = "live_game_states"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False)
    sport = Column(String, nullable=True)
    quarter_period = Column(String, nullable=True)
    time_remaining = Column(String, nullable=True)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    possession = Column(String, nullable=True)
    momentum_score = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
