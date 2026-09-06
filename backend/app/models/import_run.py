from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database.base import Base


class ImportRun(Base):
    __tablename__ = "import_runs"

    id = Column(Integer, primary_key=True)
    provider = Column(String, nullable=False)
    import_type = Column(String, nullable=False)
    season_start = Column(Integer, nullable=True)
    season_end = Column(Integer, nullable=True)
    dry_run = Column(Boolean, nullable=False, default=True, server_default="true")
    status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    rows_fetched = Column(Integer, nullable=False, default=0, server_default="0")
    teams_created = Column(Integer, nullable=False, default=0, server_default="0")
    teams_matched = Column(Integer, nullable=False, default=0, server_default="0")
    aliases_created = Column(Integer, nullable=False, default=0, server_default="0")
    games_created = Column(Integer, nullable=False, default=0, server_default="0")
    games_matched = Column(Integer, nullable=False, default=0, server_default="0")
    games_updated = Column(Integer, nullable=False, default=0, server_default="0")
    ambiguous_records = Column(Integer, nullable=False, default=0, server_default="0")
    errors_count = Column(Integer, nullable=False, default=0, server_default="0")
    checkpoint = Column(Text, nullable=True)
    source_schema_version = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )