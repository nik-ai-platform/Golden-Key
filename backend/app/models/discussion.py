from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.base import Base


class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    parent_id = Column(Integer, nullable=True, index=True)
    body = Column(Text, nullable=False)
    tags = Column(String(500), nullable=True)
    reactions = Column(String(500), nullable=True)
    likes = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
