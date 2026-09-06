from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database.base import Base


class GameProviderIdentity(Base):
    __tablename__ = "game_provider_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_game_id",
            name="uq_game_provider_identity",
        ),
        Index("ix_game_provider_identities_game_id", "game_id"),
    )

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    provider = Column(String, nullable=False)
    provider_game_id = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )