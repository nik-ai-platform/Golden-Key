from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

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

    provider_game_id = Column(
        String,
        unique=True,
        nullable=True,
        index=True
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

    home_score = Column(
        Float,
        nullable=True
    )

    away_score = Column(
        Float,
        nullable=True
    )

    winner_team_id = Column(
        Integer,
        ForeignKey("teams.id"),
        nullable=True
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

    outcomes = relationship(
        "PredictionOutcome",
        back_populates="game"
    )

    analytics = relationship(
        "AnalyticsFeature",
        back_populates="game"
        ,
        uselist=False
    )


Index(
    "idx_game_sport_date",
    Game.sport,
    Game.game_date
)


Index(
    "ix_games_game_date",
    Game.game_date,
)


Index(
    "idx_game_teams",
    Game.home_team_id,
    Game.away_team_id
)
