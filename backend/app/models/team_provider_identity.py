from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database.base import Base


class TeamProviderIdentity(Base):
    __tablename__ = "team_provider_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "sport",
            "provider_team_id",
            name="uq_team_provider_identity",
        ),
        Index("ix_team_provider_identities_team_id", "team_id"),
        Index("ix_team_provider_identities_provider_sport", "provider", "sport"),
    )

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    provider = Column(String, nullable=False)
    sport = Column(String, nullable=False)
    provider_team_id = Column(String, nullable=False)
    provider_name = Column(String, nullable=False)
    first_seen_at = Column(DateTime, nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )