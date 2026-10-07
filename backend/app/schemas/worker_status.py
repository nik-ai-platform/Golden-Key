from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


WorkerName = Literal["final-score-worker", "upcoming-game-worker"]
HealthState = Literal["disabled", "unknown", "starting", "healthy", "warning", "critical", "stopped"]
ErrorCode = Literal[
    "provider_unavailable", "invalid_source_data", "publication_failed",
    "settlement_failed", "auxiliary_failed", "worker_stopped",
    "cycle_abandoned", "telemetry_incomplete",
]


class WorkerAlert(BaseModel):
    code: Literal[
        "no_evidence", "stopped", "stale_heartbeat", "stale_progress", "failed_cycle",
        "partial_cycle", "abandoned_cycle", "incomplete_coverage", "ownership_missing",
        "competing_owners", "instance_history_truncated",
    ]
    severity: Literal["info", "warning", "critical"]
    message: str


class SourceStatus(BaseModel):
    sport: str
    league: str
    provider: str
    provider_source: str
    state: Literal["pending", "running", "succeeded", "partial", "failed", "missing"]
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    error_code: ErrorCode | None
    counters: dict[str, int | None]


class CycleStatus(BaseModel):
    id: UUID
    sequence: int
    state: Literal["running", "succeeded", "partial", "failed", "abandoned"]
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    expected_sources: int
    completed_sources: int
    failed_sources: int
    telemetry_complete: bool
    error_code: ErrorCode | None
    auxiliary_errors: int
    sources: list[SourceStatus] = Field(default_factory=list)


class InstanceStatus(BaseModel):
    id: UUID
    state: Literal["starting", "idle", "running", "stopped"]
    started_at: datetime
    heartbeat_at: datetime
    progress_at: datetime
    stopped_at: datetime | None
    poll_seconds: int
    heartbeat_seconds: int
    schedule_mode: Literal["after_completion", "start_to_start"]
    last_success_at: datetime | None
    last_success_duration_ms: int | None
    telemetry_failures: int
    ownership_held: bool | None


class WorkerStatus(BaseModel):
    worker_name: WorkerName
    health: HealthState
    alerts: list[WorkerAlert] = Field(default_factory=list)
    stale_after_seconds: int | None = None
    latest_instance: InstanceStatus | None = None
    recent_instances: list[InstanceStatus] = Field(default_factory=list)
    instance_history_truncated: bool = False
    recent_cycles: list[CycleStatus] = Field(default_factory=list)
    cycle_history_truncated: bool = False


class WorkerStatusResponse(BaseModel):
    observed_at: datetime
    telemetry_enabled: bool
    workers: list[WorkerStatus]
