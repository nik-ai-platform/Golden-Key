from datetime import datetime

from sqlalchemy import Column, DateTime, Integer

from app.database.base import Base


class UserFollow(Base):
    __tablename__ = "user_follows"

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, nullable=False, index=True)
    following_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
