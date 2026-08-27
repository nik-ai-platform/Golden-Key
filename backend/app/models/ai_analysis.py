from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)

from sqlalchemy.sql import func

from app.database.base import Base


class AIAnalysis(Base):

    __tablename__ = "ai_analysis"

    id = Column(
        Integer,
        primary_key=True
    )

    prediction_id = Column(
        Integer,
        ForeignKey(
            "predictions.id"
        ),
        nullable=False
    )

    engine_version = Column(
        String,
        default="AI-1.0"
    )

    summary = Column(
        String
    )

    explanation = Column(
        Text
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )
