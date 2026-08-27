from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.base import Base


class SharedStrategy(Base):
    __tablename__ = "shared_strategies"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, nullable=False, index=True)
    strategy_name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    sport = Column(String(80), nullable=True)
    market_type = Column(String(80), nullable=True)
    visibility = Column(String(40), nullable=False, default="public")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
