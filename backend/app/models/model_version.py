from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.database.base import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(128), nullable=False)
    version = Column(String(64), nullable=False, index=True)
    sport = Column(String(64), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    overall_accuracy = Column(Float, nullable=True)
    ats_accuracy = Column(Float, nullable=True)
    games_evaluated = Column(Integer, nullable=False, default=0)
    changes = Column(Text, nullable=True)
    performance = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="Testing")
    approved_by = Column(String(128), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
