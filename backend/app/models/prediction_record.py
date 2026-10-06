from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func

from app.database.base import Base


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("length(generation_id) = 36", name="ck_predictions_generation_id"),
        CheckConstraint(
            "length(input_fingerprint) = 64 OR input_fingerprint IN "
            "('unverified:legacy', 'unverified:manual')",
            name="ck_predictions_input_fingerprint",
        ),
        Index(
            "ix_predictions_game_model_market",
            "game_id", "model_version", "market", "generation_id",
            unique=True,
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    game_id = Column(
        Integer,
        ForeignKey("games.id"),
        nullable=False,
    )

    model_version = Column(
        String,
        default="NPI-4.0",
    )

    market = Column(
        String,
        nullable=False,
    )

    generation_id = Column(String(36), nullable=False, default=lambda: str(uuid4()))
    input_fingerprint = Column(String(64), nullable=False, default="unverified:manual")

    selection = Column(
        String,
        nullable=False,
    )

    line_value = Column(
        Float,
        nullable=True,
    )

    american_odds = Column(
        Integer,
        nullable=True,
    )

    odds_snapshot_id = Column(
        Integer,
        ForeignKey("odds.id"),
        nullable=True,
    )

    sportsbook = Column(
        String,
        nullable=True,
    )

    odds_observed_at = Column(
        DateTime,
        nullable=True,
    )

    npi_score = Column(
        Float,
        nullable=False,
    )

    win_probability = Column(
        Float,
        nullable=True,
    )

    simulation_probability = Column(
        Float,
        nullable=True,
    )

    simulation_runs = Column(
        Integer,
        nullable=True,
    )

    simulation_margin = Column(
        Float,
        nullable=True,
    )

    confidence_score = Column(
        Float,
        nullable=True,
    )

    projected_edge = Column(
        Float,
        nullable=True,
    )

    upset_signal = Column(
        Float,
        nullable=True,
    )

    risk_level = Column(
        String,
        nullable=True,
    )

    reasoning = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
    )
