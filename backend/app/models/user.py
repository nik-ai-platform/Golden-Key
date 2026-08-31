from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.sql import func

from app.core.roles import UserRole
from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True, index=True)
    recovery_email = Column(String, nullable=True, unique=True, index=True)
    recovery_email_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    hashed_password = Column(String, nullable=False)
    is_premium = Column(Boolean, default=False)
    role = Column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.VIEWER,
        server_default=UserRole.VIEWER.value,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())