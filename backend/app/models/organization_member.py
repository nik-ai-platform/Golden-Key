from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.base import Base


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(50), nullable=False, default="VIEWER")
    permissions = Column(Text, nullable=False, default="[]")
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
