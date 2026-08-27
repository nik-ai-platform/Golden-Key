from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text
)

from datetime import datetime

from app.database.base import Base


class JobExecution(Base):

    __tablename__ = "job_executions"


    id = Column(
        Integer,
        primary_key=True
    )


    job_name = Column(
        String,
        nullable=False
    )


    status = Column(
        String,
        nullable=False
    )


    attempts = Column(
        Integer,
        default=0
    )


    error_message = Column(
        Text
    )


    started_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    completed_at = Column(
        DateTime
    )
