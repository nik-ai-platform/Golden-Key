from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, text

from app.database.base import Base


class WorkerCycle(Base):
    __tablename__ = "worker_cycles"
    __table_args__ = (
        UniqueConstraint("instance_id", "sequence", name="uq_worker_cycles_instance_sequence"),
        CheckConstraint("state IN ('running', 'succeeded', 'partial', 'failed', 'abandoned')", name="ck_worker_cycles_state"),
        CheckConstraint(
            "sequence > 0 AND expected_sources >= 0 AND completed_sources >= 0 AND failed_sources >= 0 "
            "AND auxiliary_errors >= 0 AND (duration_ms IS NULL OR duration_ms >= 0)",
            name="ck_worker_cycles_counters",
        ),
        CheckConstraint("completed_sources <= expected_sources AND failed_sources <= completed_sources", name="ck_worker_cycles_source_bounds"),
        CheckConstraint(
            "(state = 'running' AND finished_at IS NULL AND duration_ms IS NULL) OR "
            "(state IN ('succeeded', 'partial', 'failed') AND finished_at IS NOT NULL AND duration_ms IS NOT NULL AND finished_at >= started_at) OR "
            "(state = 'abandoned' AND finished_at IS NOT NULL AND duration_ms IS NULL AND finished_at >= started_at)",
            name="ck_worker_cycles_terminal",
        ),
    )

    id = Column(Uuid, primary_key=True, default=uuid4)
    instance_id = Column(Uuid, ForeignKey("worker_instances.id", ondelete="CASCADE", name="fk_worker_cycles_instance"), nullable=False)
    sequence = Column(BigInteger, nullable=False)
    state = Column(String(16), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True))
    duration_ms = Column(BigInteger)
    expected_sources = Column(Integer, nullable=False)
    completed_sources = Column(Integer, nullable=False, default=0, server_default="0")
    failed_sources = Column(Integer, nullable=False, default=0, server_default="0")
    telemetry_complete = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    error_code = Column(String(48))
    auxiliary_errors = Column(Integer, nullable=False, default=0, server_default="0")


Index("uq_worker_cycles_running_instance", WorkerCycle.instance_id, unique=True,
      postgresql_where=text("state = 'running'"), sqlite_where=text("state = 'running'"))
Index("ix_worker_cycles_started", WorkerCycle.started_at.desc(), WorkerCycle.id.desc())
Index("ix_worker_cycles_instance_started", WorkerCycle.instance_id, WorkerCycle.started_at.desc(), WorkerCycle.id.desc())
