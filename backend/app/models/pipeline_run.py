from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text
)

from sqlalchemy.sql import func

from app.database.base import Base


class PipelineRun(Base):

    __tablename__ = "pipeline_runs"

    id = Column(
        Integer,
        primary_key=True
    )

    status = Column(
        String,
        default="running"
    )

    games_processed = Column(
        Integer,
        default=0
    )

    results = Column(
        Text
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )
