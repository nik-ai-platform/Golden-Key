from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import re
from typing import Callable, Mapping, TypeVar
from uuid import UUID

from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.orm import Session

from app.database.telemetry_session import TelemetryDatabase, TelemetryError, telemetry_database
from app.models.worker_cycle import WorkerCycle
from app.models.worker_cycle_source import SOURCE_COUNTERS, WorkerCycleSource
from app.models.worker_instance import WorkerInstance


INSTANCES = WorkerInstance.__table__
CYCLES = WorkerCycle.__table__
SOURCES = WorkerCycleSource.__table__
SAFE_ERROR_CODES = frozenset({
    "provider_unavailable", "invalid_source_data", "publication_failed",
    "settlement_failed", "auxiliary_failed", "worker_stopped",
    "cycle_abandoned", "telemetry_incomplete",
})
TERMINAL_SOURCES = frozenset({"succeeded", "partial", "failed", "missing"})
SOURCE_TRANSITIONS = {
    "pending": {"running", "missing"},
    "running": {"succeeded", "partial", "failed", "missing"},
}
SOURCE_TIMESTAMPS = frozenset({
    "game_date_min", "game_date_max", "last_game_processed_at",
    "latest_odds_observed_at", "latest_prediction_published_at",
})
CLEANUP_LOCK = 714_061_001
T = TypeVar("T")


class _Omitted:
    pass


OMITTED = _Omitted()


@dataclass(frozen=True)
class SourceIdentity:
    sport: str
    league: str
    provider: str
    provider_source: str

    def values(self) -> dict[str, str]:
        values = {
            "sport": self.sport, "league": self.league,
            "provider": self.provider, "provider_source": self.provider_source,
        }
        for key, limit in (("sport", 16), ("league", 32), ("provider", 32), ("provider_source", 80)):
            if not isinstance(values[key], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1," + str(limit) + "}", values[key]):
                raise TelemetryError("invalid_input")
        return values


@dataclass(frozen=True)
class PruneSummary:
    enabled: bool
    dry_run: bool
    lock_acquired: bool
    cycles: int = 0
    instances: int = 0
    batch_size: int = 500


def _time(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TelemetryError("invalid_input")
    return value.astimezone(UTC)


def _stored_time(value: datetime) -> datetime:
    # SQLite drops timezone offsets; inputs and PostgreSQL storage remain UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _integer(value: int, *, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= 9_223_372_036_854_775_807:
        raise TelemetryError("invalid_input")
    return value


def _error(code: str | None) -> str | None:
    if code is not None and code not in SAFE_ERROR_CODES:
        raise TelemetryError("invalid_error_code")
    return code


def _uuid(value: UUID) -> UUID:
    if not isinstance(value, UUID):
        raise TelemetryError("invalid_input")
    return value


class WorkerTelemetryService:
    def __init__(self, database: TelemetryDatabase = telemetry_database) -> None:
        self.database = database

    def _run(self, operation: Callable[[Session], T]) -> T | None:
        if not self.database.config.enabled:
            return None
        with self.database.transaction() as session:
            return operation(session)

    @staticmethod
    def _instance(session: Session, instance_id: UUID):
        row = session.execute(
            select(INSTANCES).where(INSTANCES.c.id == _uuid(instance_id)).with_for_update()
        ).mappings().first()
        if row is None:
            raise TelemetryError("not_found")
        return row

    @classmethod
    def _cycle(cls, session: Session, cycle_id: UUID):
        instance_id = session.scalar(select(CYCLES.c.instance_id).where(CYCLES.c.id == _uuid(cycle_id)))
        if instance_id is None:
            raise TelemetryError("not_found")
        instance = cls._instance(session, instance_id)
        cycle = session.execute(select(CYCLES).where(CYCLES.c.id == cycle_id).with_for_update()).mappings().first()
        if cycle is None:
            raise TelemetryError("not_found")
        return instance, cycle

    def register_instance(
        self, instance_id: UUID, *, worker_name: str, started_at: datetime,
        poll_seconds: int, heartbeat_seconds: int, schedule_mode: str,
        sources: tuple[SourceIdentity, ...],
    ) -> UUID | None:
        def operation(session: Session) -> UUID:
            at = _time(started_at)
            if worker_name not in {"final-score-worker", "upcoming-game-worker"} or schedule_mode not in {"after_completion", "start_to_start"}:
                raise TelemetryError("invalid_input")
            manifest = self._manifest(sources)
            values = {
                "id": _uuid(instance_id), "worker_name": worker_name, "started_at": at,
                "poll_seconds": _integer(poll_seconds, minimum=1),
                "heartbeat_seconds": _integer(heartbeat_seconds, minimum=1),
                "schedule_mode": schedule_mode, "source_manifest": manifest,
            }
            # Serialize same-ID retries without excluding independent instances.
            if session.bind is not None and session.bind.dialect.name == "postgresql":
                session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": instance_id.int % (2**63 - 1)})
            row = session.execute(select(INSTANCES).where(INSTANCES.c.id == instance_id)).mappings().first()
            if row is not None:
                if any((_stored_time(row[key]) if key == "started_at" else row[key]) != value for key, value in values.items()):
                    raise TelemetryError("conflict")
                return instance_id
            session.execute(insert(INSTANCES).values(**values, state="starting", heartbeat_at=at, progress_at=at))
            return instance_id
        return self._run(operation)

    @staticmethod
    def _manifest(sources: tuple[SourceIdentity, ...]) -> list[dict[str, str]]:
        if not isinstance(sources, tuple) or len(sources) > 32 or any(not isinstance(source, SourceIdentity) for source in sources):
            raise TelemetryError("invalid_input")
        values = [source.values() for source in sources]
        identities = [tuple(value.values()) for value in values]
        if len(set(identities)) != len(identities):
            raise TelemetryError("invalid_input")
        return sorted(values, key=lambda value: tuple(value.values()))

    def _touch(self, instance_id: UUID, at: datetime, column: str) -> bool | None:
        def operation(session: Session) -> bool:
            instant = _time(at)
            row = self._instance(session, instance_id)
            if row["state"] == "stopped":
                raise TelemetryError("illegal_transition")
            if instant <= _stored_time(row[column]):
                return False
            session.execute(update(INSTANCES).where(INSTANCES.c.id == instance_id).values({column: instant}))
            return True
        return self._run(operation)

    def update_heartbeat(self, instance_id: UUID, at: datetime) -> bool | None:
        return self._touch(instance_id, at, "heartbeat_at")

    def update_progress(self, instance_id: UUID, at: datetime) -> bool | None:
        return self._touch(instance_id, at, "progress_at")

    def begin_cycle(self, instance_id: UUID, cycle_id: UUID, *, started_at: datetime, expected_sources: int) -> int | None:
        def operation(session: Session) -> int:
            instance = self._instance(session, instance_id)
            at = _time(started_at)
            count = _integer(expected_sources)
            if count != len(instance["source_manifest"]):
                raise TelemetryError("invalid_input")
            existing = session.execute(select(CYCLES).where(CYCLES.c.id == _uuid(cycle_id))).mappings().first()
            if existing is not None:
                if existing["instance_id"] != instance_id or _stored_time(existing["started_at"]) != at or existing["expected_sources"] != count:
                    raise TelemetryError("conflict")
                return existing["sequence"]
            if instance["state"] not in {"starting", "idle"} or at < _stored_time(instance["progress_at"]):
                raise TelemetryError("illegal_transition")
            if session.scalar(select(CYCLES.c.id).where(CYCLES.c.instance_id == instance_id, CYCLES.c.state == "running")) is not None:
                raise TelemetryError("cycle_running")
            sequence = (session.scalar(select(func.max(CYCLES.c.sequence)).where(CYCLES.c.instance_id == instance_id)) or 0) + 1
            session.execute(insert(CYCLES).values(
                id=cycle_id, instance_id=instance_id, sequence=sequence, state="running",
                started_at=at, expected_sources=count,
            ))
            session.execute(update(INSTANCES).where(INSTANCES.c.id == instance_id).values(
                state="running", last_cycle_started_at=at, last_cycle_finished_at=None,
                last_cycle_outcome=None, progress_at=at,
            ))
            return sequence
        return self._run(operation)

    def register_sources(self, cycle_id: UUID, sources: tuple[SourceIdentity, ...]) -> tuple[int, ...] | None:
        def operation(session: Session) -> tuple[int, ...]:
            instance, cycle = self._cycle(session, cycle_id)
            manifest = self._manifest(sources)
            if manifest != instance["source_manifest"] or len(manifest) != cycle["expected_sources"]:
                raise TelemetryError("invalid_input")
            ids = []
            for identity in manifest:
                predicate = [SOURCES.c.cycle_id == cycle_id] + [SOURCES.c[key] == value for key, value in identity.items()]
                source_id = session.scalar(select(SOURCES.c.id).where(*predicate))
                if source_id is None:
                    if cycle["state"] != "running":
                        raise TelemetryError("illegal_transition")
                    source_id = session.execute(insert(SOURCES).values(cycle_id=cycle_id, state="pending", **identity).returning(SOURCES.c.id)).scalar_one()
                ids.append(source_id)
            return tuple(ids)
        return self._run(operation)

    def transition_source(
        self, cycle_id: UUID, source_id: int, *, state: str, at: datetime,
        duration_ms: int | None = None, counters: Mapping[str, int | None] | None = None,
        timestamps: Mapping[str, datetime | None] | None = None,
        error_code: str | None | _Omitted = OMITTED,
    ) -> bool | None:
        def operation(session: Session) -> bool:
            _, cycle = self._cycle(session, cycle_id)
            row = session.execute(select(SOURCES).where(SOURCES.c.id == _integer(source_id, minimum=1), SOURCES.c.cycle_id == cycle_id)).mappings().first()
            if row is None:
                raise TelemetryError("not_found")
            instant = _time(at)
            values: dict = {"state": state}
            if not isinstance(error_code, _Omitted):
                values["error_code"] = _error(error_code)
                if row["error_code"] is not None and error_code != row["error_code"]:
                    raise TelemetryError("conflict")
            for key, value in (counters or {}).items():
                if key not in SOURCE_COUNTERS:
                    raise TelemetryError("invalid_input")
                values[key] = None if value is None else _integer(value)
                if row[key] is not None and (value is None or value < row[key]):
                    raise TelemetryError("conflict")
            for key, value in (timestamps or {}).items():
                if key not in SOURCE_TIMESTAMPS:
                    raise TelemetryError("invalid_input")
                observation = None if value is None else _time(value)
                if row[key] is not None:
                    if observation is None:
                        raise TelemetryError("conflict")
                    aggregate = min if key == "game_date_min" else max
                    observation = aggregate(_stored_time(row[key]), observation)
                values[key] = observation
            if state == "running":
                if duration_ms is not None:
                    raise TelemetryError("invalid_input")
                values["started_at"] = _stored_time(row["started_at"]) if row["started_at"] is not None else instant
            elif state in TERMINAL_SOURCES:
                values["finished_at"] = instant
                values["duration_ms"] = _integer(duration_ms) if duration_ms is not None else None
                if duration_ms is None and state != "missing":
                    raise TelemetryError("invalid_input")
            else:
                raise TelemetryError("illegal_transition")
            if state == "succeeded" and (
                values.get("error_code", row["error_code"]) is not None
                or any((values.get(key, row[key]) or 0) > 0 for key in ("errors", "publications_failed"))
            ):
                raise TelemetryError("incomplete_source")
            if row["state"] == state:
                changed = any(
                    (_stored_time(row[key]) if isinstance(row[key], datetime) else row[key]) != value
                    for key, value in values.items()
                )
                if not changed:
                    return False
                if state != "running" or cycle["state"] != "running":
                    raise TelemetryError("conflict")
            elif state not in SOURCE_TRANSITIONS.get(row["state"], set()):
                raise TelemetryError("illegal_transition")
            if cycle["state"] != "running":
                raise TelemetryError("illegal_transition")
            if instant < _stored_time(cycle["started_at"]) or (row["started_at"] is not None and instant < _stored_time(row["started_at"])):
                raise TelemetryError("invalid_input")
            minimum = values.get("game_date_min", row["game_date_min"])
            maximum = values.get("game_date_max", row["game_date_max"])
            if minimum is not None and maximum is not None and _stored_time(maximum) < _stored_time(minimum):
                raise TelemetryError("invalid_input")
            session.execute(update(SOURCES).where(SOURCES.c.id == source_id, SOURCES.c.state == row["state"]).values(**values))
            return True
        return self._run(operation)

    def complete_cycle(
        self, cycle_id: UUID, *, state: str, finished_at: datetime, duration_ms: int,
        telemetry_complete: bool = True, auxiliary_errors: int = 0, error_code: str | None = None,
    ) -> bool | None:
        def operation(session: Session) -> bool:
            instance, cycle = self._cycle(session, cycle_id)
            at = _time(finished_at)
            rows = session.execute(select(SOURCES).where(SOURCES.c.cycle_id == cycle_id)).mappings().all()
            evidence_complete = (
                telemetry_complete and len(rows) == cycle["expected_sources"]
                and all(row["state"] in {"succeeded", "partial", "failed"} for row in rows)
            )
            values = {
                "state": state, "finished_at": at, "duration_ms": _integer(duration_ms),
                "telemetry_complete": evidence_complete, "auxiliary_errors": _integer(auxiliary_errors),
                "error_code": _error(error_code),
            }
            if state not in {"succeeded", "partial", "failed"} or type(telemetry_complete) is not bool or at < _stored_time(cycle["started_at"]):
                raise TelemetryError("invalid_input")
            if cycle["state"] == state:
                if any((_stored_time(cycle[key]) if isinstance(cycle[key], datetime) else cycle[key]) != value for key, value in values.items()):
                    raise TelemetryError("conflict")
                return False
            if cycle["state"] != "running":
                raise TelemetryError("illegal_transition")
            completed = sum(row["state"] in TERMINAL_SOURCES for row in rows)
            failed = sum(row["state"] in {"partial", "failed", "missing"} for row in rows)
            if any(row["finished_at"] is not None and _stored_time(row["finished_at"]) > at for row in rows):
                raise TelemetryError("invalid_input")
            if state == "succeeded" and (
                completed != cycle["expected_sources"] or failed or auxiliary_errors
                or not evidence_complete or error_code is not None
                or any((row["errors"] or 0) > 0 or (row["publications_failed"] or 0) > 0 or row["error_code"] is not None for row in rows)
            ):
                raise TelemetryError("incomplete_cycle")
            if state != "succeeded":
                for row in rows:
                    if row["state"] not in TERMINAL_SOURCES:
                        if row["started_at"] is not None and _stored_time(row["started_at"]) > at:
                            raise TelemetryError("invalid_input")
                        session.execute(update(SOURCES).where(SOURCES.c.id == row["id"]).values(
                            state="missing", finished_at=at, duration_ms=None,
                            error_code=row["error_code"] or "telemetry_incomplete",
                        ))
                completed = len(rows)
                failed += sum(row["state"] not in TERMINAL_SOURCES for row in rows)
            session.execute(update(CYCLES).where(CYCLES.c.id == cycle_id, CYCLES.c.state == "running").values(
                **values, completed_sources=completed, failed_sources=failed,
            ))
            instance_values = {
                "state": "idle", "last_cycle_finished_at": at, "last_cycle_outcome": state,
                "progress_at": max(at, _stored_time(instance["progress_at"])),
            }
            if state == "succeeded":
                instance_values.update(last_success_at=at, last_success_duration_ms=duration_ms)
            session.execute(update(INSTANCES).where(INSTANCES.c.id == instance["id"]).values(**instance_values))
            return True
        return self._run(operation)

    def abandon_cycle(self, cycle_id: UUID, *, stale_before: datetime, at: datetime) -> bool | None:
        def operation(session: Session) -> bool:
            instance, cycle = self._cycle(session, cycle_id)
            cutoff, instant = _time(stale_before), _time(at)
            if cutoff > instant or instant < _stored_time(cycle["started_at"]):
                raise TelemetryError("invalid_input")
            if cycle["state"] != "running" or _stored_time(instance["heartbeat_at"]) >= cutoff or _stored_time(instance["progress_at"]) >= cutoff:
                return False
            rows = session.execute(select(SOURCES).where(SOURCES.c.cycle_id == cycle_id)).mappings().all()
            chronology = [
                _stored_time(cycle["started_at"]),
                _stored_time(instance["heartbeat_at"]), _stored_time(instance["progress_at"]),
            ]
            for row in rows:
                chronology.extend(
                    _stored_time(row[key])
                    for key in (
                        "started_at", "finished_at", "last_game_processed_at",
                        "latest_odds_observed_at", "latest_prediction_published_at",
                    )
                    if row[key] is not None
                )
            if instant < max(chronology):
                raise TelemetryError("invalid_input")
            session.execute(update(SOURCES).where(SOURCES.c.cycle_id == cycle_id, SOURCES.c.state.in_(["pending", "running"])).values(
                state="missing", finished_at=instant, duration_ms=None,
                error_code=func.coalesce(SOURCES.c.error_code, "cycle_abandoned"),
            ))
            session.execute(update(CYCLES).where(CYCLES.c.id == cycle_id, CYCLES.c.state == "running").values(
                state="abandoned", finished_at=instant, duration_ms=None,
                completed_sources=len(rows), failed_sources=sum(row["state"] != "succeeded" for row in rows),
                telemetry_complete=False, error_code="cycle_abandoned",
            ))
            session.execute(update(INSTANCES).where(INSTANCES.c.id == instance["id"]).values(
                state="stopped", stopped_at=instant, last_cycle_finished_at=instant, last_cycle_outcome="abandoned",
            ))
            return True
        return self._run(operation)

    def stop_instance(self, instance_id: UUID, at: datetime) -> bool | None:
        def operation(session: Session) -> bool:
            row = self._instance(session, instance_id)
            instant = _time(at)
            if row["state"] == "stopped":
                if _stored_time(row["stopped_at"]) != instant:
                    raise TelemetryError("conflict")
                return False
            if row["state"] == "running" or instant < max(_stored_time(row["heartbeat_at"]), _stored_time(row["progress_at"])):
                raise TelemetryError("illegal_transition")
            session.execute(update(INSTANCES).where(INSTANCES.c.id == instance_id).values(state="stopped", stopped_at=instant))
            return True
        return self._run(operation)

    def increment_failure_count(self, instance_id: UUID, *, expected_count: int) -> int | None:
        def operation(session: Session) -> int:
            row = self._instance(session, instance_id)
            expected = _integer(expected_count)
            count = expected + 1
            if row["telemetry_failures"] == count:
                return count
            if row["telemetry_failures"] != expected:
                raise TelemetryError("conflict")
            _integer(count)
            session.execute(update(INSTANCES).where(INSTANCES.c.id == instance_id).values(telemetry_failures=count))
            return count
        return self._run(operation)

    def prune_history(
        self, *, at: datetime, retention_days: int = 30, batch_size: int = 500, dry_run: bool = False,
    ) -> PruneSummary:
        if not self.database.config.enabled:
            return PruneSummary(False, dry_run, False, batch_size=batch_size)
        def operation(session: Session) -> PruneSummary:
            if type(dry_run) is not bool or type(batch_size) is not int or not 1 <= batch_size <= 500 or type(retention_days) is not int or not 1 <= retention_days <= 365:
                raise TelemetryError("invalid_input")
            cutoff = _time(at) - timedelta(days=retention_days)
            if session.bind is not None and session.bind.dialect.name == "postgresql":
                acquired = session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": CLEANUP_LOCK})
                if not acquired:
                    return PruneSummary(True, dry_run, False, batch_size=batch_size)
            # Lock instance rows first, matching lifecycle writers. Keep the latest
            # cycle of nonretired instances as the durable sequence anchor.
            retired = list(session.scalars(select(INSTANCES.c.id).where(
                INSTANCES.c.state == "stopped", INSTANCES.c.stopped_at < cutoff,
                INSTANCES.c.heartbeat_at < cutoff, INSTANCES.c.progress_at < cutoff,
            ).order_by(INSTANCES.c.stopped_at, INSTANCES.c.id).limit(batch_size).with_for_update(skip_locked=True)))
            latest = select(func.max(CYCLES.c.sequence)).where(CYCLES.c.instance_id == INSTANCES.c.id).correlate(INSTANCES).scalar_subquery()
            eligible = select(CYCLES.c.id).join(INSTANCES, INSTANCES.c.id == CYCLES.c.instance_id).where(
                CYCLES.c.state != "running", CYCLES.c.finished_at < cutoff,
                (CYCLES.c.sequence < latest) | CYCLES.c.instance_id.in_(retired),
            ).order_by(CYCLES.c.finished_at, CYCLES.c.id).limit(batch_size).with_for_update(skip_locked=True)
            cycles = list(session.scalars(eligible))
            if not dry_run and cycles:
                session.execute(delete(CYCLES).where(CYCLES.c.id.in_(cycles)))
            remaining = select(CYCLES.c.id).where(CYCLES.c.instance_id == INSTANCES.c.id)
            if dry_run and cycles:
                remaining = remaining.where(CYCLES.c.id.not_in(cycles))
            instances = list(session.scalars(select(INSTANCES.c.id).where(
                INSTANCES.c.id.in_(retired), ~remaining.exists(),
            ).order_by(INSTANCES.c.id).limit(batch_size - len(cycles))))
            if not dry_run and instances:
                session.execute(delete(INSTANCES).where(INSTANCES.c.id.in_(instances)))
            return PruneSummary(True, dry_run, True, len(cycles), len(instances), batch_size)
        result = self._run(operation)
        if result is None:
            raise TelemetryError("disabled")
        return result
