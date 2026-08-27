from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.base import Base


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, nullable=False, index=True)
    game_id = Column(Integer, nullable=False, index=True)
    market = Column(String(100), nullable=False)
    stake = Column(Float, nullable=False)
    odds = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    status = Column(String(30), nullable=False, default="open")
    result = Column(String(30), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
