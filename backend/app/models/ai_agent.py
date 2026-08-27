from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.base import Base


class AIAgent(Base):
    __tablename__ = "ai_agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    agent_type = Column(String(64), nullable=False)
    version = Column(String(32), nullable=False, default="1.0")
    status = Column(String(32), nullable=False, default="active")
    performance_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
