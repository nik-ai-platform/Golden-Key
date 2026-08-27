from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.base import Base


class ResearchKnowledge(Base):
    __tablename__ = "research_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    discovery = Column(String(1000), nullable=False)
    evidence = Column(Text, nullable=False)
    sport = Column(String(50), nullable=False)
    confidence = Column(String(30), nullable=False, default="medium")
    source = Column(String(120), nullable=False, default="autonomous_research")
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
