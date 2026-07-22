from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class AnalyticsFeature(Base):

    __tablename__ = "analytics_features"

    id = Column(
        Integer,
        primary_key=True
    )

    game_id = Column(
        Integer,
        ForeignKey("games.id"),
        unique=True,
        nullable=False
    )

    home_rest_days = Column(Integer)

    away_rest_days = Column(Integer)

    line_movement = Column(Float)

    implied_home_probability = Column(Float)

    implied_away_probability = Column(Float)

    favorite_is_home = Column(Boolean)

    home_back_to_back = Column(Boolean)

    away_back_to_back = Column(Boolean)

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

    game = relationship(
        "Game",
        back_populates="analytics"
    )
