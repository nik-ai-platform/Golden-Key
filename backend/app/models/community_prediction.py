from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.base import Base


class CommunityPrediction(Base):
    __tablename__ = "community_predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    game_id = Column(Integer, nullable=True, index=True)
    prediction = Column(String(300), nullable=False)
    confidence = Column(Integer, nullable=False, default=0)
    analysis = Column(String(2000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
