from collections.abc import Mapping
from datetime import UTC, datetime
import math
from typing import Literal

from sqlalchemy import select, text

from app.database.telemetry_session import TelemetryDatabase, TelemetryError, telemetry_database
from app.database.worker_ownership import ownership_key
from app.models.worker_cycle import WorkerCycle
from app.models.worker_cycle_source import SOURCE_COUNTERS, WorkerCycleSource
from app.models.worker_instance import WorkerInstance
from app.schemas.worker_status import (
    CycleStatus, InstanceStatus, SourceStatus, WorkerAlert, WorkerName,
    WorkerStatus, WorkerStatusResponse,
)


WORKERS: tuple[WorkerName, ...] = ("final-score-worker", "upcoming-game-worker")
HISTORY_LIMIT = 10
SOURCE_HISTORY_LIMIT = HISTORY_LIMIT * 32


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def normalized(row: Mapping[str, object]) -> dict[str, object]:
    return {key: utc(value) if isinstance(value, datetime) else value for key, value in row.items()}


def classify_worker(worker: WorkerStatus, now: datetime, grace_seconds: int) -> None:
    instance = worker.latest_instance
    if instance is None:
        worker.health = "unknown"
        worker.alerts.append(WorkerAlert(code="no_evidence", severity="info", message="No worker evidence has been recorded."))
        return

    def alert(code: Literal["stale_heartbeat", "stale_progress", "ownership_missing", "competing_owners"], message: str) -> None:
        worker.alerts.append(WorkerAlert(code=code, severity="critical", message=message))

    duration = math.ceil((instance.last_success_duration_ms or 0) / 1000)
    threshold = instance.poll_seconds * 2 + grace_seconds + duration
    worker.stale_after_seconds = threshold
    starting = (now - utc(instance.started_at)).total_seconds() <= grace_seconds
    if instance.state == "stopped":
        worker.alerts.append(WorkerAlert(code="stopped", severity="warning", message="The latest instance recorded a stop."))
    else:
        if (now - utc(instance.heartbeat_at)).total_seconds() > threshold:
            alert("stale_heartbeat", "Heartbeat is older than the polling-aware freshness threshold.")
        if (now - utc(instance.progress_at)).total_seconds() > threshold:
            alert("stale_progress", "Main-loop progress is older than the polling-aware freshness threshold.")
        if instance.ownership_held is False and not starting:
            alert("ownership_missing", "The latest instance has no retained telemetry ownership lock.")
    if sum(i.ownership_held is True for i in worker.recent_instances) > 1:
        alert("competing_owners", "Multiple retained telemetry owners were observed for this worker.")
    # A running cycle has incomplete evidence by definition; classify the latest terminal cycle.
    terminal = next((c for c in worker.recent_cycles if c.state != "running"), None)
    if terminal is not None:
        if terminal.state in {"failed", "abandoned", "partial"}:
            code = {"failed": "failed_cycle", "abandoned": "abandoned_cycle", "partial": "partial_cycle"}[terminal.state]
            worker.alerts.append(WorkerAlert(
                code=code, severity="warning" if terminal.state == "partial" else "critical",
                message=f"The latest completed cycle is {terminal.state}.",
            ))
        if not terminal.telemetry_complete:
            worker.alerts.append(WorkerAlert(code="incomplete_coverage", severity="warning", message="The latest completed cycle has incomplete source evidence."))
    if worker.instance_history_truncated:
        worker.alerts.append(WorkerAlert(code="instance_history_truncated", severity="warning", message="Instance history is bounded; additional owners may exist outside this view."))
    if any(a.severity == "critical" for a in worker.alerts):
        worker.health = "critical"
    elif instance.state == "stopped":
        worker.health = "stopped"
    elif any(a.severity == "warning" for a in worker.alerts):
        worker.health = "warning"
    elif starting and (terminal is None or instance.ownership_held is False):
        worker.health = "starting"
    elif (
        instance.ownership_held is not True or terminal is None
        or any(i.ownership_held is None for i in worker.recent_instances)
    ):
        worker.health = "unknown"
    else:
        worker.health = "healthy"


class WorkerStatusService:
    def __init__(self, database: TelemetryDatabase = telemetry_database, *, grace_seconds: int = 120) -> None:
        self.database = database
        self.grace_seconds = grace_seconds

    def read(self, *, at: datetime | None = None) -> WorkerStatusResponse:
        now = utc(at or datetime.now(UTC))
        enabled = self.database.config.enabled
        response = WorkerStatusResponse(
            observed_at=now, telemetry_enabled=enabled,
            workers=[WorkerStatus(worker_name=name, health="disabled" if not enabled else "unknown") for name in WORKERS],
        )
        if not enabled:
            return response
        with self.database.transaction() as session:
            postgres = self.database.engine.dialect.name == "postgresql"
            if postgres:
                session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            for worker in response.workers:
                rows = session.execute(
                    select(WorkerInstance.__table__).where(WorkerInstance.worker_name == worker.worker_name)
                    .order_by(WorkerInstance.started_at.desc(), WorkerInstance.id.desc()).limit(HISTORY_LIMIT + 1)
                ).mappings().all()
                worker.instance_history_truncated = len(rows) > HISTORY_LIMIT
                for row in rows[:HISTORY_LIMIT]:
                    held = None
                    if postgres:
                        key = ownership_key(row["id"]) & ((1 << 64) - 1)
                        # pg_locks merges session and transaction advisory locks.
                        # Only a holder outside a transaction proves retained ownership.
                        held = session.scalar(text(
                            "SELECT CASE WHEN count(*)=0 THEN false "
                            "WHEN bool_or(a.state='idle' AND a.xact_start IS NULL) THEN true "
                            "ELSE NULL END FROM pg_locks l "
                            "LEFT JOIN pg_stat_activity a ON a.pid=l.pid "
                            "WHERE l.locktype='advisory' AND l.mode='ExclusiveLock' "
                            "AND l.classid=:high AND l.objid=:low AND l.objsubid=1 AND l.granted "
                            "AND l.database=(SELECT oid FROM pg_database WHERE datname=current_database())"
                        ), {"high": key >> 32, "low": key & 0xFFFFFFFF})
                    worker.recent_instances.append(InstanceStatus.model_validate(normalized(row) | {"ownership_held": held}))
                worker.latest_instance = next(iter(worker.recent_instances), None)
                if worker.latest_instance is not None:
                    cycles = session.execute(
                        select(WorkerCycle.__table__).where(WorkerCycle.instance_id == worker.latest_instance.id)
                        .order_by(WorkerCycle.sequence.desc()).limit(HISTORY_LIMIT + 1)
                    ).mappings().all()
                    worker.cycle_history_truncated = len(cycles) > HISTORY_LIMIT
                    worker.recent_cycles = [CycleStatus.model_validate(normalized(row)) for row in cycles[:HISTORY_LIMIT]]
                    if worker.recent_cycles:
                        sources = session.execute(
                            select(WorkerCycleSource.__table__).where(
                                WorkerCycleSource.cycle_id.in_([c.id for c in worker.recent_cycles])
                            ).order_by(WorkerCycleSource.sport, WorkerCycleSource.league, WorkerCycleSource.provider_source)
                            .limit(SOURCE_HISTORY_LIMIT + 1)
                        ).mappings().all()
                        if len(sources) > SOURCE_HISTORY_LIMIT:
                            raise TelemetryError("invalid_evidence")
                        for cycle in worker.recent_cycles:
                            cycle.sources = [
                                SourceStatus.model_validate(normalized(source) | {"counters": {k: source[k] for k in SOURCE_COUNTERS}})
                                for source in sources if source["cycle_id"] == cycle.id
                            ]
                classify_worker(worker, now, self.grace_seconds)
        return response
