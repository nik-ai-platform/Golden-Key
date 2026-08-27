from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.base import Base


class ModelExperiment(Base):

    __tablename__ = "model_experiments"

    id = Column(Integer, primary_key=True)

    experiment_name = Column(String, nullable=True)

    sport = Column(String, nullable=True)

    base_model_version = Column(String, nullable=True)

    candidate_version = Column(String, nullable=True)

    experiment_type = Column(String, nullable=True)

    configuration = Column(String, nullable=True)

    status = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    completed_at = Column(DateTime, nullable=True)
