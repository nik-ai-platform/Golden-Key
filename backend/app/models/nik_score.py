from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

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

    game = relationship(
        "Game",
        back_populates="nik_scores"
    )
