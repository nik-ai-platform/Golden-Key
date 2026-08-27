from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.base import Base


class ResearchTask(Base):
    __tablename__ = "research_tasks"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, nullable=False, index=True)
    objective = Column(String(1000), nullable=False)
    sport = Column(String(50), nullable=False)
    priority = Column(String(30), nullable=False, default="medium")
    status = Column(String(30), nullable=False, default="queued")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    result = Column(Text, nullable=True)
