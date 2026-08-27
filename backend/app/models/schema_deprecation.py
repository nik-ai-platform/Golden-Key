from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database.base import Base


class SchemaDeprecation(Base):
    __tablename__ = "schema_deprecations"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(128), nullable=False, unique=True, index=True)
    replacement_table = Column(String(128), nullable=True)
    deprecated = Column(Boolean, nullable=False, default=True)
    deprecated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    removal_after = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default="deprecated")
    notes = Column(Text, nullable=True)
