from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class MarketValue(Base):

    __tablename__ = "market_values"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)

    market_type = Column(String, nullable=False)

    model_projection = Column(Float, nullable=True)

    market_line = Column(Float, nullable=True)

    edge = Column(Float, nullable=True)

    value_score = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    game = relationship("Game")


Index("ix_market_values_game_id", MarketValue.game_id)
