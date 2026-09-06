from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database.base import Base


class TeamSeason(Base):
    __tablename__ = "team_seasons"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "season",
            "source_provider",
            name="uq_team_season_source",
        ),
    )

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season = Column(Integer, nullable=False)
    conference_name = Column(String, nullable=True)
    classification = Column(String, nullable=True)
    division = Column(String, nullable=True)
    is_fbs = Column(Boolean, nullable=True)
    source_provider = Column(String, nullable=False)
    observed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )