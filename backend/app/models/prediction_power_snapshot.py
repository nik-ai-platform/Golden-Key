from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database.base import Base


class PredictionPowerSnapshot(Base):
    __tablename__ = "prediction_power_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "model_version",
            "rating_as_of",
            name="uq_prediction_power_snapshot",
        ),
    )

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    model_version = Column(String, nullable=False)
    rating_as_of = Column(DateTime(timezone=True), nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_rating = Column(Float, nullable=False)
    away_rating = Column(Float, nullable=False)
    home_uncertainty = Column(Float, nullable=False)
    away_uncertainty = Column(Float, nullable=False)
    home_games_used = Column(Integer, nullable=False)
    away_games_used = Column(Integer, nullable=False)
    home_effective_games = Column(Float, nullable=False)
    away_effective_games = Column(Float, nullable=False)
    minimum_games_used = Column(Integer, nullable=False)
    combined_uncertainty = Column(Float, nullable=False)
    neutral_site = Column(Boolean, nullable=False)
    home_field_points = Column(Float, nullable=False)
    independent_model_margin = Column(Float, nullable=False)
    source_max_observed_at = Column(DateTime(timezone=True), nullable=False)
    training_game_count = Column(Integer, nullable=False)
    input_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


Index("ix_prediction_power_snapshot_game_id", PredictionPowerSnapshot.game_id)
Index("ix_prediction_power_snapshot_input_hash", PredictionPowerSnapshot.input_hash)