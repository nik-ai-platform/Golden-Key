from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String
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

    spread_home_price = Column(Integer, nullable=True)
    spread_away_price = Column(Integer, nullable=True)
    total_over_price = Column(Integer, nullable=True)
    total_under_price = Column(Integer, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    game = relationship(
        "Game",
        back_populates="odds"
    )


Index(
    "ix_odds_game_book_created_id",
    Odds.game_id,
    Odds.sportsbook,
    Odds.created_at,
    Odds.id,
)
