from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database.base import Base


class NcaafPowerMarketShadowRecord(Base):
    __tablename__ = "ncaaf_power_market_shadow_records"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "power_model_version",
            "shadow_spec_version",
            name="uq_ncaaf_power_market_shadow_record",
        ),
        Index(
            "ix_ncaaf_shadow_record_provenance_generated",
            "generation_provenance",
            "generated_at",
        ),
    )

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    power_model_version = Column(String, nullable=False)
    shadow_spec_version = Column(String, nullable=False)
    generation_provenance = Column(String, nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=False)
    rating_as_of = Column(DateTime(timezone=True), nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    neutral_site = Column(Boolean, nullable=False)
    home_rating = Column(Float, nullable=False)
    away_rating = Column(Float, nullable=False)
    home_games_used = Column(Integer, nullable=False)
    away_games_used = Column(Integer, nullable=False)
    home_effective_games = Column(Float, nullable=False)
    away_effective_games = Column(Float, nullable=False)
    home_uncertainty = Column(Float, nullable=False)
    away_uncertainty = Column(Float, nullable=False)
    combined_uncertainty = Column(Float, nullable=False)
    independent_model_margin = Column(Float, nullable=False)
    odds_snapshot_id = Column(Integer, ForeignKey("odds.id"), nullable=False)
    sportsbook = Column(String, nullable=True)
    odds_created_at = Column(DateTime(timezone=True), nullable=False)
    spread_home = Column(Float, nullable=False)
    spread_away = Column(Float, nullable=True)
    market_margin = Column(Float, nullable=False)
    disagreement = Column(Float, nullable=False)
    abs_disagreement = Column(Float, nullable=False)
    p_home_cover_shadow = Column(Float, nullable=False)
    shadow_side = Column(String, nullable=False)
    p_selected_shadow = Column(Float, nullable=False)
    spread_price = Column(Integer, nullable=False)
    price_source = Column(String, nullable=False)
    break_even_probability = Column(Float, nullable=False)
    shadow_edge = Column(Float, nullable=False)
    evidence_gate_pass = Column(Boolean, nullable=False)
    spread_safety_gate_pass = Column(Boolean, nullable=False)
    power_input_hash = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


Index("ix_ncaaf_shadow_record_game_id", NcaafPowerMarketShadowRecord.game_id)
Index(
    "ix_ncaaf_shadow_record_odds_snapshot_id",
    NcaafPowerMarketShadowRecord.odds_snapshot_id,
)
Index(
    "ix_ncaaf_shadow_record_power_input_hash",
    NcaafPowerMarketShadowRecord.power_input_hash,
)