from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database.base import Base


class PredictionLineCorrection(Base):
    __tablename__ = "prediction_line_corrections"

    id = Column(Integer, primary_key=True)
    prediction_id = Column(
        Integer,
        ForeignKey("predictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_line = Column(Float, nullable=True)
    corrected_line = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())