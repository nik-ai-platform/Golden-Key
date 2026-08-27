from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

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

    selection = Column(
        String,
        nullable=False,
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
