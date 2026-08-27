from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), default="")
    permissions: Mapped[str] = mapped_column(Text, default="[]")
    owner: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    quota: Mapped[int] = mapped_column(Integer, default=1000)
    rate_limit: Mapped[int] = mapped_column(Integer, default=60)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @staticmethod
    def generate_key() -> str:
        raw = secrets.token_urlsafe(24)
        return f"gk_live_{raw}"

    @staticmethod
    def hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()
