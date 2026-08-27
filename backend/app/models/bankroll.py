from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer

from app.database.base import Base


class Bankroll(Base):

    __tablename__ = "bankrolls"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, nullable=True)

    total_amount = Column(Float, nullable=True)

    unit_percentage = Column(Float, nullable=True)

    max_daily_risk = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
