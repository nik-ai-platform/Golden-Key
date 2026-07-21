from sqlalchemy import Column, Integer, String, Float

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
