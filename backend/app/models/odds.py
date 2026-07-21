from sqlalchemy import Column, Float, Integer, String

from app.database.base import Base


class Odds(Base):

    __tablename__ = "odds"

    id = Column(
        Integer,
        primary_key=True
    )

    game_id = Column(
        Integer
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
