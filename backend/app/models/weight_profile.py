from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy.sql import func

from app.database.base import Base


class WeightProfile(Base):

    __tablename__ = "weight_profiles"

    id = Column(
        Integer,
        primary_key=True,
    )

    sport = Column(
        String,
        nullable=False,
        index=True,
    )

    model_version = Column(
        String,
        nullable=False,
        index=True,
    )

    profile_name = Column(
        String,
        nullable=False,
    )

    # Flexible feature-to-weight payload so new features do not require schema changes.
    weights_json = Column(
        JSON,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=False,
    )


Index(
    "ix_weight_profiles_sport_version_active",
    WeightProfile.sport,
    WeightProfile.model_version,
    WeightProfile.is_active,
)
