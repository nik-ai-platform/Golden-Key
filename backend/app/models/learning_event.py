from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.database.base import Base


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(128), nullable=False)
    event_type = Column(String(64), nullable=False)
    input_data = Column(Text, nullable=False)
    prediction = Column(Text, nullable=False)
    actual_result = Column(Text, nullable=True)
    error_score = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
