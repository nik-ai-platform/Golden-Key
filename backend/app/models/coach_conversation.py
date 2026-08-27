from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, JSON

from app.database.base import Base


class CoachConversation(Base):
    __tablename__ = "coach_conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    message = Column(String, nullable=False)
    response = Column(String, nullable=False)
    context = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
