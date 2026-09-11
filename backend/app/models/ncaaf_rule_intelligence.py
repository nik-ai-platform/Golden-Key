from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.database.base import Base


class NcaafRuleIntelligence(Base):
    __tablename__ = "ncaaf_rule_intelligence"
    __table_args__ = (
        CheckConstraint(
            "rule_team_location IN ('HOME', 'AWAY')",
            name="ck_ncaaf_rule_intelligence_team_location",
        ),
        CheckConstraint(
            "rule_semantics IN ('COVERS', 'DOES_NOT_COVER')",
            name="ck_ncaaf_rule_intelligence_semantics",
        ),
        CheckConstraint(
            "rule_pick_side IN ('HOME', 'AWAY')",
            name="ck_ncaaf_rule_intelligence_pick_side",
        ),
        CheckConstraint(
            "npi_selection IN ('HOME', 'AWAY', 'PASS')",
            name="ck_ncaaf_rule_intelligence_npi_selection",
        ),
        CheckConstraint(
            "comparison IN ('AGREE', 'DISAGREE', 'NPI_PASS')",
            name="ck_ncaaf_rule_intelligence_comparison",
        ),
        CheckConstraint(
            "rule_result IS NULL OR rule_result IN ('WIN', 'LOSS', 'PUSH')",
            name="ck_ncaaf_rule_intelligence_rule_result",
        ),
        CheckConstraint(
            "npi_result IS NULL OR npi_result IN ('WIN', 'LOSS', 'PUSH')",
            name="ck_ncaaf_rule_intelligence_npi_result",
        ),
    )

    id = Column(Integer, primary_key=True)
    prediction_id = Column(
        Integer,
        ForeignKey("predictions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    odds_snapshot_id = Column(Integer, ForeignKey("odds.id"), nullable=False, index=True)
    model_version = Column(String, nullable=False)
    rule_code = Column(String, nullable=False, index=True)
    rule_team_location = Column(String, nullable=False)
    rule_spread = Column(Float, nullable=False)
    rule_semantics = Column(String, nullable=False)
    rule_pick_side = Column(String, nullable=False)
    rule_pick_line = Column(Float, nullable=False)
    npi_selection = Column(String, nullable=False)
    comparison = Column(String, nullable=False, index=True)
    rule_result = Column(String, nullable=True)
    npi_result = Column(String, nullable=True)
    settled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "ix_ncaaf_rule_intelligence_rule_comparison",
    NcaafRuleIntelligence.rule_code,
    NcaafRuleIntelligence.comparison,
)