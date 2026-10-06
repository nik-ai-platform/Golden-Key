from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Index, Integer, JSON, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB

from app.database.base import Base


class WorkerInstance(Base):
    __tablename__ = "worker_instances"
    __table_args__ = (
        CheckConstraint("worker_name IN ('final-score-worker', 'upcoming-game-worker')", name="ck_worker_instances_name"),
        CheckConstraint("state IN ('starting', 'idle', 'running', 'stopped')", name="ck_worker_instances_state"),
        CheckConstraint("schedule_mode IN ('after_completion', 'start_to_start')", name="ck_worker_instances_schedule_mode"),
        CheckConstraint("poll_seconds > 0 AND heartbeat_seconds > 0", name="ck_worker_instances_intervals"),
        CheckConstraint(
            "heartbeat_at >= started_at AND progress_at >= started_at "
            "AND (stopped_at IS NULL OR (stopped_at >= heartbeat_at AND stopped_at >= progress_at)) "
            "AND ((state = 'stopped' AND stopped_at IS NOT NULL) OR (state <> 'stopped' AND stopped_at IS NULL)) "
            "AND (last_cycle_started_at IS NULL OR last_cycle_started_at >= started_at) "
            "AND (last_cycle_finished_at IS NULL OR (last_cycle_started_at IS NOT NULL AND last_cycle_finished_at >= last_cycle_started_at)) "
            "AND (last_success_at IS NULL OR last_success_at >= started_at) "
            "AND ((last_success_at IS NULL AND last_success_duration_ms IS NULL) OR "
            "(last_success_at IS NOT NULL AND last_success_duration_ms IS NOT NULL)) "
            "AND ((last_cycle_finished_at IS NULL AND last_cycle_outcome IS NULL) OR "
            "(last_cycle_finished_at IS NOT NULL AND last_cycle_outcome IS NOT NULL)) "
            "AND (last_cycle_outcome IS NULL OR last_cycle_outcome IN ('succeeded', 'partial', 'failed', 'abandoned'))",
            name="ck_worker_instances_timestamps",
        ),
        CheckConstraint("telemetry_failures >= 0 AND (last_success_duration_ms IS NULL OR last_success_duration_ms >= 0)", name="ck_worker_instances_counters"),
        CheckConstraint("jsonb_typeof(source_manifest) = 'array'", name="ck_worker_instances_manifest").ddl_if(dialect="postgresql"),
        CheckConstraint("json_type(source_manifest) = 'array'", name="ck_worker_instances_manifest").ddl_if(dialect="sqlite"),
    )

    id = Column(Uuid, primary_key=True, default=uuid4)
    worker_name = Column(String(40), nullable=False)
    state = Column(String(16), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    heartbeat_at = Column(DateTime(timezone=True), nullable=False)
    progress_at = Column(DateTime(timezone=True), nullable=False)
    stopped_at = Column(DateTime(timezone=True))
    poll_seconds = Column(Integer, nullable=False)
    heartbeat_seconds = Column(Integer, nullable=False)
    schedule_mode = Column(String(24), nullable=False)
    source_manifest = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    last_cycle_started_at = Column(DateTime(timezone=True))
    last_cycle_finished_at = Column(DateTime(timezone=True))
    last_cycle_outcome = Column(String(16))
    last_success_at = Column(DateTime(timezone=True))
    last_success_duration_ms = Column(BigInteger)
    telemetry_failures = Column(BigInteger, nullable=False, default=0, server_default="0")


Index("ix_worker_instances_name_started", WorkerInstance.worker_name, WorkerInstance.started_at.desc(), WorkerInstance.id.desc())
Index("ix_worker_instances_heartbeat", WorkerInstance.heartbeat_at)
