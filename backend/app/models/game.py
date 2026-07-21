from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from app.database.base import Base


game_teams = Table(
    "game_teams",
    Base.metadata,
    Column("game_id", Integer, ForeignKey("games.id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("teams.id"), primary_key=True),
)


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True, nullable=True)
    title = Column(String, nullable=False)
    sport = Column(String, nullable=False)
    status = Column(String, default="scheduled")
    starts_at = Column(DateTime, nullable=True)

    odds = relationship("Odds", back_populates="game")
    nik_scores = relationship("NikScore", back_populates="game")
    teams = relationship("Team", secondary="game_teams", back_populates="games")
