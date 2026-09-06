from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database.base import Base


class GameResultObservation(Base):
    __tablename__ = "game_result_observations"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    provider = Column(String, nullable=False)
    home_score = Column(Float, nullable=True)
    away_score = Column(Float, nullable=True)
    status = Column(String, nullable=False)
    observed_at = Column(DateTime, nullable=False)
    source_updated_at = Column(DateTime, nullable=True)
    payload_hash = Column(String, nullable=True)
    import_run_id = Column(Integer, ForeignKey("import_runs.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())