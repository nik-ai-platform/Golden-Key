from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func

from app.database.base import Base


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"
    __table_args__ = (
        Index("ix_feature_snapshot_prediction", "prediction_id"),
        Index("ix_feature_snapshot_model", "model_version"),
        Index("ix_feature_snapshot_feature_name", "feature_name"),
    )

    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey("nik_scores.id"), nullable=False)
    feature_name = Column(String, nullable=False)
    feature_value = Column(Float, nullable=False)
    model_version = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())