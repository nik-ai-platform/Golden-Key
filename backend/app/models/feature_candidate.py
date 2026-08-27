from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.base import Base


class FeatureCandidate(Base):

    __tablename__ = "feature_candidates"

    id = Column(Integer, primary_key=True)

    feature_name = Column(String, nullable=True)

    sport = Column(String, nullable=True)

    category = Column(String, nullable=True)

    description = Column(String, nullable=True)

    importance_score = Column(Integer, nullable=True)

    correlation_score = Column(Integer, nullable=True)

    validation_status = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
