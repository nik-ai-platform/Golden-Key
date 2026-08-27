from sqlalchemy import Column, Float, Integer, String

from app.database.base import Base


class GameState(Base):
    __tablename__ = "game_states"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, nullable=False, index=True)
    offensive_strength = Column(Float, nullable=False, default=0.0)
    defensive_strength = Column(Float, nullable=False, default=0.0)
    pace = Column(Float, nullable=False, default=0.0)
    efficiency = Column(Float, nullable=False, default=0.0)
    turnover_rate = Column(Float, nullable=False, default=0.0)
    red_zone_ability = Column(Float, nullable=False, default=0.0)
    explosive_plays = Column(Float, nullable=False, default=0.0)
    fatigue = Column(Float, nullable=False, default=0.0)
