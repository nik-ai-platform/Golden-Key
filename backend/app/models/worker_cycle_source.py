from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Identity, Index, Integer, String, UniqueConstraint, Uuid

from app.database.base import Base


SOURCE_COUNTERS = (
    "fetched", "processed", "created", "refreshed", "usable_odds", "skipped_no_odds",
    "prediction_rows_returned", "prediction_rows_created", "publications_created",
    "publications_reused", "publications_skipped", "publications_failed", "matched",
    "finalized", "already_final", "unmatched", "skipped_not_final", "games_settled",
    "prediction_results_created", "errors",
)


class WorkerCycleSource(Base):
    __tablename__ = "worker_cycle_sources"
    __table_args__ = (
        UniqueConstraint("cycle_id", "sport", "league", "provider", "provider_source", name="uq_worker_cycle_sources_identity"),
        CheckConstraint("state IN ('pending', 'running', 'succeeded', 'partial', 'failed', 'missing')", name="ck_worker_cycle_sources_state"),
        CheckConstraint(" AND ".join(f"({name} IS NULL OR {name} >= 0)" for name in SOURCE_COUNTERS) + " AND (duration_ms IS NULL OR duration_ms >= 0)", name="ck_worker_cycle_sources_counters"),
        CheckConstraint("game_date_min IS NULL OR game_date_max IS NULL OR game_date_max >= game_date_min", name="ck_worker_cycle_sources_dates"),
        CheckConstraint(
            "(state = 'pending' AND started_at IS NULL AND finished_at IS NULL AND duration_ms IS NULL) OR "
            "(state = 'running' AND started_at IS NOT NULL AND finished_at IS NULL AND duration_ms IS NULL) OR "
            "(state IN ('succeeded', 'partial', 'failed') AND started_at IS NOT NULL AND finished_at IS NOT NULL "
            "AND finished_at >= started_at AND duration_ms IS NOT NULL) OR "
            "(state = 'missing' AND finished_at IS NOT NULL "
            "AND (started_at IS NULL OR finished_at >= started_at))",
            name="ck_worker_cycle_sources_terminal",
        ),
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), Identity(), primary_key=True)
    cycle_id = Column(Uuid, ForeignKey("worker_cycles.id", ondelete="CASCADE", name="fk_worker_cycle_sources_cycle"), nullable=False)
    sport = Column(String(16), nullable=False)
    league = Column(String(32), nullable=False)
    provider = Column(String(32), nullable=False)
    provider_source = Column(String(80), nullable=False)
    state = Column(String(16), nullable=False)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    duration_ms = Column(BigInteger)
    error_code = Column(String(48))
    game_date_min = Column(DateTime(timezone=True))
    game_date_max = Column(DateTime(timezone=True))
    last_game_processed_at = Column(DateTime(timezone=True))
    latest_odds_observed_at = Column(DateTime(timezone=True))
    latest_prediction_published_at = Column(DateTime(timezone=True))
    fetched = Column(BigInteger)
    processed = Column(BigInteger)
    created = Column(BigInteger)
    refreshed = Column(BigInteger)
    usable_odds = Column(BigInteger)
    skipped_no_odds = Column(BigInteger)
    prediction_rows_returned = Column(BigInteger)
    prediction_rows_created = Column(BigInteger)
    publications_created = Column(BigInteger)
    publications_reused = Column(BigInteger)
    publications_skipped = Column(BigInteger)
    publications_failed = Column(BigInteger)
    matched = Column(BigInteger)
    finalized = Column(BigInteger)
    already_final = Column(BigInteger)
    unmatched = Column(BigInteger)
    skipped_not_final = Column(BigInteger)
    games_settled = Column(BigInteger)
    prediction_results_created = Column(BigInteger)
    errors = Column(BigInteger)


Index("ix_worker_cycle_sources_lookup", WorkerCycleSource.sport, WorkerCycleSource.league, WorkerCycleSource.provider_source, WorkerCycleSource.cycle_id)
