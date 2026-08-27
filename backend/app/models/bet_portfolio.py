from sqlalchemy import Column, Float, Integer, String

from app.database.base import Base


class BetPortfolio(Base):

    __tablename__ = "bet_portfolios"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, nullable=True)

    bet_id = Column(Integer, nullable=True)

    stake = Column(Float, nullable=True)

    odds = Column(Float, nullable=True)

    potential_return = Column(Float, nullable=True)

    status = Column(String, nullable=True)

    result = Column(String, nullable=True)
