from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
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

    win_percentage = Column(
        Float
    )

    avg_points_for = Column(
        Float
    )

    avg_points_against = Column(
        Float
    )

    home_win_percentage = Column(
        Float
    )

    away_win_percentage = Column(
        Float
    )

    current_streak = Column(
        Integer
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