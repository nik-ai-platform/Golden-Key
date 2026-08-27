from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.database.base import Base


class PredictionOutput(Base):
    __tablename__ = "predictions_unified"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    model_version = Column(String(50), nullable=False, default="NPI-v1")
    pick = Column(String(100), nullable=False)
    market = Column(String(50), nullable=False, default="spread")
    confidence = Column(Float, nullable=False, default=0.0)
    npi_score = Column(Float, nullable=False, default=0.0)
    simulation_probability = Column(Float, nullable=False, default=0.0)
    risk_score = Column(String(20), nullable=False, default="medium")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
