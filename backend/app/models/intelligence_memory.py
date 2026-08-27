from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.database.base import Base


class IntelligenceMemory(Base):
    __tablename__ = "intelligence_memory"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(1000), nullable=False)
    reasoning = Column(Text, nullable=False)
    outcome = Column(Text, nullable=False)
    lesson = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=0.5)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
