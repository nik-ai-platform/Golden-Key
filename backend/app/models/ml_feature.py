from datetime import datetime
from datetime import UTC

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MLFeature(Base):
    __tablename__ = "ml_features"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    game_id: Mapped[int | None] = mapped_column(index=True, nullable=True)
    sport: Mapped[str | None] = mapped_column(String(50), nullable=True)
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_value: Mapped[float] = mapped_column(Float, nullable=False)
    feature_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
