from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Float

from app.database.base import Base


class GameEvent(Base):
    __tablename__ = "game_events"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False)
    event_type = Column(String, nullable=True)
    team = Column(String, nullable=True)
    description = Column(String, nullable=True)
    impact = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
