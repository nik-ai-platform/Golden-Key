from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class NikScore(Base):

    __tablename__ = "nik_scores"

    id = Column(
        Integer,
        primary_key=True
    )

    game_id = Column(
        Integer,
        ForeignKey("games.id")
    )

    ats_score = Column(
        Float
    )

    ml_score = Column(
        Float
    )

    total_score = Column(
        Float
    )

    final_npi = Column(
        Float
    )

    home_score = Column(
        Float
    )

    away_score = Column(
        Float
    )

    confidence = Column(
        Float
    )

    confidence_level = Column(
        String
    )

    model_version = Column(
        String,
        default="NPI-v1"
    )

    recommendation = Column(
        String
    )

    explanation = Column(
        JSON
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    game = relationship(
        "Game",
        back_populates="nik_scores"
    )

    outcomes = relationship(
        "PredictionOutcome",
        back_populates="prediction"
    )


Index(
    "ix_nik_scores_game_id",
    NikScore.game_id,
)


Index(
    "ix_nik_scores_created_at",
    NikScore.created_at,
)
