from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database.base import Base


class TeamAlias(Base):
    __tablename__ = "team_aliases"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "provider",
            "normalized_alias",
            name="uq_team_alias_provider_name",
        ),
        Index("ix_team_aliases_normalized_alias", "normalized_alias"),
        Index("ix_team_aliases_team_id", "team_id"),
    )

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    provider = Column(String, nullable=True)
    alias_name = Column(String, nullable=False)
    normalized_alias = Column(String, nullable=False)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    confidence = Column(Float, nullable=True)
    review_state = Column(
        String,
        nullable=False,
        default="unreviewed",
        server_default="unreviewed",
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )