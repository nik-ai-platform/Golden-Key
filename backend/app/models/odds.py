from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

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

    spread = Column(
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

    sportsbook = Column(
        String
    )

    game = relationship(
        "Game",
        back_populates="odds"
    )
