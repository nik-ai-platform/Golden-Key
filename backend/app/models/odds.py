from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Odds(Base):

    __tablename__ = "odds"

    id = Column(
        Integer,
        primary_key=True
    )

    game_id = Column(
        Integer,
        ForeignKey("games.id")
    )

    sportsbook = Column(
        String
    )

    spread_home = Column(
        Float
    )

    spread_away = Column(
        Float
    )

    moneyline_home = Column(
        Integer
    )

    moneyline_away = Column(
        Integer
    )

    total = Column(
        Float
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    game = relationship(
        "Game",
        back_populates="odds"
    )
