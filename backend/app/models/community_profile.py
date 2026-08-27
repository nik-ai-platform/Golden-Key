from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database.base import Base


class CommunityProfile(Base):
    __tablename__ = "community_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(80), nullable=False, index=True)
    display_name = Column(String(120), nullable=True)
    bio = Column(String(500), nullable=True)
    avatar = Column(String(500), nullable=True)
    verified_status = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
