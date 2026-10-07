from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import logging
import math
import sys
import time
from typing import Callable, Iterator, Mapping, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.database.telemetry_session import TelemetryDatabase, TelemetryError, telemetry_database
from app.database.worker_ownership import OwnershipLease, WorkerOwnership
from app.models.worker_cycle import WorkerCycle
from app.models.worker_instance import WorkerInstance
from app.services.sport_mapping_service import SportMappingService
from app.services.worker_telemetry_service import SourceIdentity, WorkerTelemetryService


logger = logging.getLogger(__name__)
T = TypeVar("T")
ACTIVE: ContextVar[WorkerInstrumentation | None] = ContextVar("worker_instrumentation", default=None)


@dataclass
class SourceEvidence:
    started_at: datetime
    monotonic_start: float
    counters: dict[str, int] = field(default_factory=dict)
    timestamps: dict[str, datetime] = field(default_factory=dict)
    finished_at: datetime | None = None
    duration_ms: int | None = None
    state: str | None = None
    error_code: str | None = None
    fetched: bool = False


class WorkerInstrumentation:
    """Buffers observations; storage calls occur only outside business sessions."""

    def __init__(
        self, worker_name: str, sports: tuple[str, ...], poll_seconds: int,
        schedule_mode: str, *, database: TelemetryDatabase = telemetry_database,
    ) -> None:
        self.database = database
        self.worker_name = worker_name
        self.poll_seconds = poll_seconds
        self.schedule_mode = schedule_mode
        self.instance_id = uuid4()
        self.cycle_id: UUID | None = None
        self.service = WorkerTelemetryService(database)
        self.enabled = False
        self.sources: tuple[SourceIdentity, ...] = ()
        self.ids: dict[SourceIdentity, int] = {}
        self.evidence: dict[SourceIdentity, SourceEvidence] = {}
        self.flushed: set[SourceIdentity] = set()
        self.auxiliary_errors = 0
        self.cycle_start = 0.0
        self._last_time = datetime.now(UTC)
        self._warned = False
        self._cleanup_deadline: float | None = None
        self._business_session_open = False
        self.ownership = WorkerOwnership(database)
        self._lease: OwnershipLease | None = None
        try:
            self.enabled = database.config.enabled
            if self.enabled:
                mapping = SportMappingService()
                try:
                    self.sources = tuple(
                        SourceIdentity(sport, source.league, "odds_api", source.provider_key)
                        for sport in sports for source in mapping.competition_sources(sport)
                    )
                except ValueError:
                    raise TelemetryError("invalid_configuration") from None
                if len(set(self.sources)) != len(self.sources) or len(self.sources) > 32:
                    raise TelemetryError("invalid_configuration")
                for source in self.sources:
                    source.values()
        except TelemetryError:
            self._degrade()

    def _now(self) -> datetime:
        self._last_time = max(self._last_time, datetime.now(UTC))
        return self._last_time

    def _degrade(self) -> None:
        self.begin_cleanup()
        self.enabled = False
        self._release_ownership(discard=True)
        if not self._warned:
            logger.warning("Worker telemetry unavailable worker=%s code=telemetry_unavailable", self.worker_name)
            self._warned = True

    def _call(self, operation: Callable[[], T]) -> T | None:
        if not self.enabled:
            return None
        if self._business_session_open:
            self._degrade()
            return None
        if self._cleanup_deadline is not None and time.monotonic() >= self._cleanup_deadline:
            self._degrade()
            return None
        try:
            if self._lease is not None:
                self._lease.check()
            if self._cleanup_deadline is not None and time.monotonic() >= self._cleanup_deadline:
                self._degrade()
                return None
            return operation()
        except (TelemetryError, SQLAlchemyError):
            self._degrade()
            return None

    def register(self) -> None:
        def own() -> None:
            if self.ownership.supported:
                self._lease = self.ownership.acquire(self.instance_id, on_unwind=self.begin_cleanup)
                if self._lease is None:
                    raise TelemetryError("ownership_unavailable")
        self._call(own)
        self._call(lambda: self.service.register_instance(
            self.instance_id, worker_name=self.worker_name, started_at=self._now(),
            poll_seconds=self.poll_seconds, heartbeat_seconds=self.poll_seconds,
            schedule_mode=self.schedule_mode, sources=self.sources,
        ))
        self.recover_stale_cycles()

    def recover_stale_cycles(self) -> None:
        def recover() -> None:
            if not self.ownership.supported:
                return
            now = self._now()
            # Only telemetry tables are read; abandonment rechecks under lifecycle locks.
            with self.database.transaction() as session:
                candidates = session.execute(
                    select(
                        WorkerCycle.id, WorkerInstance.id.label("owner_id"), WorkerInstance.poll_seconds,
                        WorkerInstance.last_success_duration_ms,
                        WorkerInstance.heartbeat_at, WorkerInstance.progress_at,
                    ).join(WorkerInstance, WorkerInstance.id == WorkerCycle.instance_id)
                    .where(
                        WorkerInstance.worker_name == self.worker_name,
                        WorkerInstance.id != self.instance_id, WorkerCycle.state == "running",
                        WorkerInstance.heartbeat_at < now - timedelta(seconds=self.poll_seconds * 2),
                        WorkerInstance.progress_at < now - timedelta(seconds=self.poll_seconds * 2),
                    ).order_by(WorkerCycle.started_at, WorkerCycle.id).limit(32)
                ).all()
            from app.database.telemetry_session import _settings
            grace = _settings().OPERATIONS_STARTUP_GRACE_SECONDS
            for row in candidates:
                seconds = row.poll_seconds * 2 + grace + math.ceil((row.last_success_duration_ms or 0) / 1000)
                self.service.abandon_cycle(
                    row.id, stale_before=now - timedelta(seconds=seconds), at=now,
                    recovery_owner=row.owner_id,
                )
        self._call(recover)

    def heartbeat(self) -> None:
        self._call(lambda: self.service.update_heartbeat(self.instance_id, self._now()))

    def business_session_opened(self) -> None:
        self._business_session_open = True

    def business_session_closed(self) -> None:
        self._business_session_open = False

    def progress(self) -> None:
        self._call(lambda: self.service.update_progress(self.instance_id, self._now()))

    def start_cycle(self) -> None:
        if not self.enabled:
            return
        self._cleanup_deadline = None
        self.evidence.clear()
        self.flushed.clear()
        self.auxiliary_errors = 0
        self.cycle_id = uuid4()
        self.cycle_start = time.monotonic()
        self.heartbeat()
        self._call(lambda: self.service.begin_cycle(
            self.instance_id, self.cycle_id, started_at=self._now(), expected_sources=len(self.sources),
        ))
        identifiers = self._call(lambda: self.service.register_sources(self.cycle_id, self.sources))
        if identifiers is not None:
            ordered = sorted(self.sources, key=lambda source: tuple(source.values().values()))
            self.ids = dict(zip(ordered, identifiers))

    def source(self, sport: str, provider_source: str) -> SourceIdentity | None:
        return next(
            (source for source in self.sources if source.sport == sport and source.provider_source == provider_source),
            None,
        )

    def start_source(self, source: SourceIdentity) -> None:
        if self.enabled and source not in self.evidence:
            self.evidence[source] = SourceEvidence(self._now(), time.monotonic())

    def update_source(
        self, source: SourceIdentity, *, counters: Mapping[str, int] | None = None,
        timestamps: Mapping[str, datetime] | None = None, error_code: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        self.start_source(source)
        evidence = self.evidence[source]
        for key, value in (counters or {}).items():
            evidence.counters[key] = max(evidence.counters.get(key, 0), value)
        for key, value in (timestamps or {}).items():
            at = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
            aggregate = min if key == "game_date_min" else max
            evidence.timestamps[key] = aggregate(evidence.timestamps.get(key, at), at)
        if error_code is not None:
            evidence.error_code = evidence.error_code or error_code

    def finish_source(self, source: SourceIdentity, *, failed: bool = False) -> None:
        if not self.enabled:
            return
        evidence = self.evidence[source]
        if evidence.finished_at is not None:
            return
        evidence.finished_at = self._now()
        evidence.duration_ms = max(0, int((time.monotonic() - evidence.monotonic_start) * 1000))
        errors = evidence.counters.get("errors", 0) > 0 or evidence.error_code is not None
        evidence.state = "failed" if failed else "partial" if errors else "succeeded"

    def wrap_fetch(self, sport: str, fetch: Callable[..., T]) -> Callable[..., T]:
        def observed(provider_source: str, *args, **kwargs) -> T:
            key = SportMappingService().provider_key(provider_source)
            source = self.source(sport, key)
            if source is not None:
                self.start_source(source)
            try:
                result = fetch(provider_source, *args, **kwargs)
            except Exception:
                if source is not None:
                    self.update_source(source, counters={"errors": 1}, error_code="provider_unavailable")
                raise
            if source is not None and self.enabled and isinstance(result, list):
                self.evidence[source].fetched = True
            return result
        return observed

    def flush_sport(self, sport: str) -> None:
        if not self.enabled:
            return
        for source in self.sources:
            if source.sport != sport or source in self.flushed:
                continue
            evidence = self.evidence.get(source)
            if evidence is None:
                continue
            identifier = self.ids[source]
            self._call(lambda: self.service.transition_source(
                self.cycle_id, identifier, state="running", at=evidence.started_at,
            ))
            self._call(lambda: self.service.transition_source(
                self.cycle_id, identifier, state="running", at=evidence.started_at,
                counters=evidence.counters, timestamps=evidence.timestamps, error_code=evidence.error_code,
            ))
            if evidence.finished_at is not None:
                self._call(lambda: self.service.transition_source(
                    self.cycle_id, identifier, state=evidence.state, at=evidence.finished_at,
                    duration_ms=evidence.duration_ms,
                ))
                self.flushed.add(source)
                if self.enabled:
                    logger.info(
                        "Worker telemetry source worker=%s sport=%s league=%s provider_source=%s state=%s",
                        self.worker_name, source.sport, source.league, source.provider_source, evidence.state,
                    )
        self.heartbeat()
        self.progress()

    def auxiliary_failed(self) -> None:
        if self.enabled:
            self.auxiliary_errors += 1

    def observed_game(self, sport: str, provider_source: str, *, failed: bool = False) -> None:
        if not self.enabled:
            return
        source = self.source(sport, provider_source)
        if source is not None:
            self.update_source(
                source,
                timestamps={} if failed else {"last_game_processed_at": self._now()},
                error_code="publication_failed" if failed else None,
            )

    def observed_source_processing(self, source: SourceIdentity) -> None:
        self.update_source(source, timestamps={"last_game_processed_at": self._now()})

    def finish_cycle(self, *, interrupted: bool = False) -> None:
        if not self.enabled or self.cycle_id is None:
            return
        for sport in dict.fromkeys(
            source.sport for source in self.evidence if source not in self.flushed
        ):
            self.flush_sport(sport)
        states = [self.evidence[source].state if source in self.evidence else None for source in self.sources]
        complete = all(state is not None for state in states) and not interrupted
        success = complete and all(state == "succeeded" for state in states) and not self.auxiliary_errors
        state = "succeeded" if success else "partial" if any(
            state in {"succeeded", "partial"} for state in states
        ) else "failed"
        self._call(lambda: self.service.complete_cycle(
            self.cycle_id, state=state, finished_at=self._now(),
            duration_ms=max(0, int((time.monotonic() - self.cycle_start) * 1000)),
            telemetry_complete=complete, auxiliary_errors=self.auxiliary_errors,
            error_code="worker_stopped" if interrupted else None,
        ))
        if self.enabled:
            logger.info(
                "Worker telemetry cycle worker=%s state=%s telemetry_complete=%s",
                self.worker_name, state, complete,
            )
        self.cycle_id = None
        self.heartbeat()

    def shutdown(self) -> None:
        self.begin_cleanup()
        if self.cycle_id is not None:
            self.finish_cycle(interrupted=True)
        self._call(lambda: self.service.stop_instance(self.instance_id, self._now()))
        self._release_ownership()

    def begin_cleanup(self) -> None:
        if self.enabled and self._cleanup_deadline is None:
            self._cleanup_deadline = time.monotonic() + 3

    def _release_ownership(self, *, discard: bool = False) -> None:
        lease, self._lease = self._lease, None
        try:
            if lease is not None:
                lease.close(self._cleanup_deadline, discard=discard)
        except TelemetryError:
            self.enabled = False
            if not self._warned:
                logger.warning("Worker telemetry unavailable worker=%s code=telemetry_unavailable", self.worker_name)
                self._warned = True
        finally:
            try:
                self.ownership.dispose()
            except TelemetryError:
                self.enabled = False
                if not self._warned:
                    logger.warning("Worker telemetry unavailable worker=%s code=telemetry_unavailable", self.worker_name)
                    self._warned = True

    @contextmanager
    def process(self) -> Iterator[WorkerInstrumentation]:
        token = None
        started = False
        try:
            self.register()
            token = ACTIVE.set(self)
            started = True
            yield self
        finally:
            unwinding = sys.exc_info()[0] is not None
            self.begin_cleanup()
            try:
                if started:
                    self.shutdown()
                else:
                    self._release_ownership()
            except BaseException:
                if not unwinding:
                    raise
                self.enabled = False
                if not self._warned:
                    logger.warning("Worker telemetry unavailable worker=%s code=telemetry_unavailable", self.worker_name)
                    self._warned = True
            finally:
                if token is not None:
                    ACTIVE.reset(token)

    @contextmanager
    def cycle(self) -> Iterator[WorkerInstrumentation]:
        self.start_cycle()
        try:
            yield self
        except BaseException:
            self.begin_cleanup()
            self.finish_cycle(interrupted=True)
            raise
        else:
            self.finish_cycle()


@contextmanager
def worker_cycle(worker_name: str, sports: tuple[str, ...], poll_seconds: int, schedule_mode: str):
    current = ACTIVE.get()
    if current is not None:
        with current.cycle():
            yield current
    else:
        with WorkerInstrumentation(worker_name, sports, poll_seconds, schedule_mode).process() as recorder:
            with recorder.cycle():
                yield recorder
