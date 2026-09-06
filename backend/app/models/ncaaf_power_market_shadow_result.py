from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.sql import func

from app.database.base import Base


class NcaafPowerMarketShadowResult(Base):
    __tablename__ = "ncaaf_power_market_shadow_results"
    __table_args__ = (
        UniqueConstraint(
            "shadow_record_id",
            name="uq_ncaaf_power_market_shadow_result",
        ),
    )

    id = Column(Integer, primary_key=True)
    shadow_record_id = Column(
        Integer,
        ForeignKey("ncaaf_power_market_shadow_records.id"),
        nullable=False,
    )
    home_score = Column(Float, nullable=False)
    away_score = Column(Float, nullable=False)
    actual_home_margin = Column(Float, nullable=False)
    model_margin_error = Column(Float, nullable=False)
    market_margin_error = Column(Float, nullable=False)
    model_absolute_error = Column(Float, nullable=False)
    market_absolute_error = Column(Float, nullable=False)
    settled_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )