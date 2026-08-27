from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database.base import Base


class NPIWeightProfile(Base):

    __tablename__ = "npi_weight_profiles"
    __table_args__ = (
        UniqueConstraint(
            "sport",
            "model_version",
            "factor_name",
            name="uq_npi_weight_profile_factor",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String, nullable=False, index=True)
    model_version = Column(String, nullable=False, index=True)
    factor_name = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
