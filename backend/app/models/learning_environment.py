from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.base import Base


class LearningEnvironment(Base):
    __tablename__ = "learning_environments"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String(64), nullable=False)
    market_type = Column(String(64), nullable=False)
    team_context = Column(Text, nullable=False)
    market_conditions = Column(Text, nullable=False)
    environment_state = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
