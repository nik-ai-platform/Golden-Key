from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Boolean, Float

from app.database.base import Base


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    prediction_helpful = Column(Boolean, nullable=True)
    recommendation_used = Column(Boolean, nullable=True)
    confidence_accuracy = Column(Float, nullable=True)
    user_rating = Column(Integer, nullable=True)
    comments = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
