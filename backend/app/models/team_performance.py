from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class TeamPerformance(Base):

    __tablename__ = "team_performance"

    id = Column(
        Integer,
        primary_key=True
    )

    team_id = Column(
        Integer,
        ForeignKey("teams.id"),
        nullable=False
    )

    games_played = Column(
        Integer,
        default=0
    )

    wins = Column(
        Integer,
        default=0
    )

    losses = Column(
        Integer,
        default=0
    )

    points_for_avg = Column(
        Float
    )

    points_against_avg = Column(
        Float
    )

    recent_form = Column(
        Float
    )

    home_record = Column(
        Float
    )

    away_record = Column(
        Float
    )

    offensive_rating = Column(
        Float
    )

    defensive_rating = Column(
        Float
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    team = relationship(
        "Team",
        back_populates="performance"
    )


Index(
    "ix_team_performance_team_id",
    TeamPerformance.team_id,
)