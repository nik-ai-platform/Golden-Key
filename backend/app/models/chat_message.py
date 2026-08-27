from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    tokens_used = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
