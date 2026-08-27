from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.database.base import Base


class BacktestResult(Base):

    __tablename__ = "backtest_results"


    id = Column(
        Integer,
        primary_key=True
    )


    backtest_id = Column(
        Integer,
        nullable=True,
        index=True,
    )


    game_id = Column(
        Integer,
        ForeignKey("games.id"),
        nullable=True,
    )


    predicted_side = Column(
        String,
        nullable=True,
    )


    actual_side = Column(
        String,
        nullable=True,
    )


    spread = Column(
        Float,
        nullable=True,
    )


    npi_score = Column(
        Float,
        nullable=True,
    )


    confidence = Column(
        Float,
        nullable=True,
    )


    win_loss = Column(
        String,
        nullable=True,
    )


    profit_loss = Column(
        Float,
        nullable=True,
    )


    model_version = Column(
        String,
        nullable=False,
    )


    sport = Column(
        String,
        nullable=False,
    )


    market = Column(
        String,
        nullable=False,
    )


    outcome = Column(
        String,
        nullable=False,
    )


    start_date = Column(
        Date,
        nullable=True,
    )


    end_date = Column(
        Date,
        nullable=True,
    )


    games_tested = Column(
        Integer,
        nullable=True,
    )


    accuracy = Column(
        Float
    )


    ats_record = Column(
        String,
        nullable=True,
    )


    roi = Column(
        Float,
        nullable=True,
    )


    calibration_error = Column(
        Float,
        nullable=True,
    )


    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


    total_predictions = Column(
        Integer,
        nullable=True,
    )


    correct_predictions = Column(
        Integer,
        nullable=True,
    )


    average_confidence = Column(
        Float,
        nullable=True,
    )
