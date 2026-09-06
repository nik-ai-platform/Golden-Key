from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database.base import Base


class TeamPowerRatingRecord(Base):
    __tablename__ = "team_power_rating_records"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "model_version",
            "rating_as_of",
            name="uq_team_power_rating_snapshot",
        ),
        Index("ix_team_power_rating_season_as_of", "sport", "season", "rating_as_of"),
    )

    id = Column(Integer, primary_key=True)
    sport = Column(String, nullable=False)
    season = Column(Integer, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    model_version = Column(String, nullable=False)
    rating = Column(Float, nullable=False)
    uncertainty = Column(Float, nullable=False)
    games_used = Column(Integer, nullable=False)
    effective_games = Column(Float, nullable=False)
    rating_as_of = Column(DateTime(timezone=True), nullable=False)
    source_max_observed_at = Column(DateTime(timezone=True), nullable=False)
    training_game_count = Column(Integer, nullable=False)
    input_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


Index("ix_team_power_rating_team_id", TeamPowerRatingRecord.team_id)
Index("ix_team_power_rating_input_hash", TeamPowerRatingRecord.input_hash)