from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship

from app.database.base import Base


class Team(Base):

    __tablename__ = "teams"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    league = Column(
        String,
        nullable=False
    )

    sport = Column(
        String,
        nullable=False
    )

    power_rating = Column(
        Float,
        default=0
    )

    home_games = relationship(
        "Game",
        foreign_keys="Game.home_team_id",
        back_populates="home_team"
    )

    away_games = relationship(
        "Game",
        foreign_keys="Game.away_team_id",
        back_populates="away_team"
    )

    performance = relationship(
        "TeamPerformance",
        back_populates="team",
        uselist=False
    )
