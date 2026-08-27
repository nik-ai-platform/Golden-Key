from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime
)

from sqlalchemy.sql import func

from app.database.base import Base


class NPIFactorResult(Base):

    __tablename__ = "npi_factor_results"

    id = Column(Integer, primary_key=True)

    prediction_id = Column(
        Integer,
        ForeignKey("predictions.id"),
        nullable=False
    )

    factor_name = Column(String, nullable=False)

    weight = Column(Float, nullable=False)

    factor_score = Column(Float, nullable=False)

    predicted_side = Column(String)

    actual_outcome = Column(String)

    created_at = Column(
        DateTime,
        server_default=func.now()
    )