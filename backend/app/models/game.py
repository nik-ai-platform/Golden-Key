from sqlalchemy import Column, Integer, DateTime, String, Float

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

    home_team = Column(
        String,
        nullable=False
    )

    away_team = Column(
        String,
        nullable=False
    )

    spread = Column(
        Float
    )

    total = Column(
        Float
    )

    home_score = Column(
        Integer
    )

    away_score = Column(
        Integer
    )

    result = Column(
        String
    )
