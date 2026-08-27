from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.base import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, nullable=False, index=True)
    simulation_count = Column(Integer, nullable=False)
    model_version = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="queued")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    results = Column(Text, nullable=True)
