from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Game(Base):

    __tablename__ = "games"

    id = Column(
        Integer,
        primary_key=True
    )

    sport = Column(
        String,
        nullable=False
    )

    league = Column(
        String,
        nullable=False
    )

    season = Column(
        Integer
    )

    home_team_id = Column(
        Integer,
        ForeignKey("teams.id"),
        nullable=False
    )

    away_team_id = Column(
        Integer,
        ForeignKey("teams.id"),
        nullable=False
    )

    game_date = Column(
        DateTime,
        nullable=False
    )

    status = Column(
        String,
        nullable=False
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    home_team = relationship(
        "Team",
        foreign_keys=[home_team_id],
        back_populates="home_games"
    )

    away_team = relationship(
        "Team",
        foreign_keys=[away_team_id],
        back_populates="away_games"
    )

    odds = relationship(
        "Odds",
        back_populates="game"
    )

    nik_scores = relationship(
        "NikScore",
        back_populates="game"
    )
