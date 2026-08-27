from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.base import Base


class SportsKnowledge(Base):
    __tablename__ = "sports_knowledge"

    ENTITY_TYPES = (
        "Teams",
        "Players",
        "Coaches",
        "Strategies",
        "Markets",
        "Conditions",
        "Historical Events",
        "Trends",
    )

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(120), nullable=False, index=True)
    relationship = Column(String(120), nullable=False)
    attribute = Column(String(200), nullable=False)
    confidence = Column(Float, nullable=False, default=0.5)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
