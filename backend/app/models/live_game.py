from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.base import Base


class LiveGame(Base):

    __tablename__ = "live_games"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, nullable=True)

    quarter_period = Column(String, nullable=True)

    home_score = Column(Integer, nullable=True)

    away_score = Column(Integer, nullable=True)

    clock = Column(String, nullable=True)

    possession = Column(String, nullable=True)

    momentum_score = Column(Float, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
