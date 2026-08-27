from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, JSON

from app.database.base import Base


class SportConfiguration(Base):
    __tablename__ = "sport_configurations"

    id = Column(Integer, primary_key=True)
    sport_name = Column(String, nullable=False)
    model_version = Column(String, nullable=True)
    active_features = Column(JSON, nullable=True)
    weight_configuration = Column(JSON, nullable=True)
    market_types = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
