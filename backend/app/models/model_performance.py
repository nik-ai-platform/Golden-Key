from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.database.base import Base


class ModelPerformance(Base):

    __tablename__ = "model_performances"


    id = Column(
        Integer,
        primary_key=True
    )


    model_name = Column(String, nullable=True)
    model_version = Column(String, nullable=False)
    accuracy = Column(Float)
    ats_percentage = Column(Float)
    roi = Column(Float)
    calibration = Column(Float)
    confidence_error = Column(Float)
    recent_performance = Column(Text)
    historical_performance = Column(Text)
    total_predictions = Column(Integer)
    average_confidence = Column(Float)
    status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
