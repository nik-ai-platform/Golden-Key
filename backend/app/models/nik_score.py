from sqlalchemy import Column, Integer, Float, String

from app.database.base import Base


class NikScore(Base):

    __tablename__ = "nik_scores"

    id = Column(
        Integer,
        primary_key=True
    )

    game_id = Column(
        Integer
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

    recommendation = Column(
        String
    )
