from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.base import Base


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, index=True)
    decision = Column(String(128), nullable=False)
    environment = Column(Text, nullable=False)
    outcome = Column(Text, nullable=False)
    reward = Column(String(64), nullable=False)
    lesson_learned = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
