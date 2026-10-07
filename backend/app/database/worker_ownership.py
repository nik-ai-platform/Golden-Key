from __future__ import annotations

from hashlib import blake2b
import logging
import sys
import time
from typing import Callable
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.database.telemetry_session import TelemetryDatabase, TelemetryError


logger = logging.getLogger(__name__)


def ownership_key(instance_id: UUID | str) -> int:
    if isinstance(instance_id, str):
        if len(instance_id) != 36:
            raise TelemetryError("invalid_input")
        try:
            normalized = UUID(instance_id)
        except ValueError:
            raise TelemetryError("invalid_input") from None
        if str(normalized) != instance_id.lower():
            raise TelemetryError("invalid_input")
        instance_id = normalized
    if not isinstance(instance_id, UUID):
        raise TelemetryError("invalid_input")
    digest = blake2b(b"golden-key:worker-ownership:v1:" + instance_id.bytes, digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


class OwnershipLease:
    def __init__(self, connection: Connection, key: int) -> None:
        self.connection = connection
        self.key = key

    def check(self) -> None:
        if self.connection.closed or self.connection.invalidated:
            raise TelemetryError("ownership_unavailable")
        unsigned = self.key & ((1 << 64) - 1)
        try:
            held = self.connection.scalar(text(
                "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype = 'advisory' "
                "AND pid = pg_backend_pid() AND classid = :high AND objid = :low "
                "AND objsubid = 1 AND granted)"
            ), {"high": unsigned >> 32, "low": unsigned & 0xFFFFFFFF})
            self.connection.commit()
            if not held:
                raise TelemetryError("ownership_unavailable")
        except SQLAlchemyError:
            raise TelemetryError("ownership_unavailable") from None

    def close(self, deadline: float | None = None, *, discard: bool = False) -> None:
        try:
            if (
                not discard and not self.connection.closed and not self.connection.invalidated
                and (deadline is None or time.monotonic() < deadline)
            ):
                self.connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": self.key})
                self.connection.commit()
        except SQLAlchemyError:
            raise TelemetryError("ownership_unavailable") from None
        finally:
            # Never return a session lock to a pool or perform a network rollback.
            try:
                try:
                    self.connection.invalidate()
                finally:
                    self.connection.close()
            except SQLAlchemyError:
                raise TelemetryError("ownership_unavailable") from None


class WorkerOwnership:
    """Session locks use independent, non-pooled telemetry connections."""

    def __init__(self, database: TelemetryDatabase) -> None:
        self.database = database
        self._engine: Engine | None = None
        self._connections: set[Connection] = set()

    @property
    def supported(self) -> bool:
        return self.database.engine.dialect.name == "postgresql"

    def acquire(
        self, instance_id: UUID | str, *, on_unwind: Callable[[], None] | None = None,
    ) -> OwnershipLease | None:
        key = ownership_key(instance_id)
        if not self.supported:
            return None
        connection = None
        retained = False
        try:
            if self._engine is None:
                config = self.database.config
                self._engine = create_engine(
                    self.database.engine.url, poolclass=NullPool, hide_parameters=True,
                    connect_args={
                        "connect_timeout": config.connect_timeout_seconds,
                        "options": (
                            f"-c statement_timeout={config.statement_timeout_ms} "
                            f"-c lock_timeout={config.lock_timeout_ms} -c timezone=UTC"
                        ),
                    },
                )
            connection = self._engine.connect()
            self._connections.add(connection)
            acquired = connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
            connection.commit()
            if acquired:
                lease = OwnershipLease(connection, key)
                retained = True
                return lease
            return None
        except SQLAlchemyError:
            raise TelemetryError("ownership_unavailable") from None
        finally:
            if not retained and connection is not None:
                self._connections.discard(connection)
                unwinding = sys.exc_info()[0] is not None
                if unwinding and on_unwind is not None:
                    on_unwind()
                try:
                    try:
                        connection.invalidate()
                    finally:
                        connection.close()
                except BaseException as error:
                    if unwinding:
                        logger.warning("Worker ownership cleanup failed code=ownership_unavailable")
                    elif isinstance(error, SQLAlchemyError):
                        raise TelemetryError("ownership_unavailable") from None
                    else:
                        raise

    def dispose(self) -> None:
        connections, self._connections = self._connections, set()
        try:
            for connection in connections:
                if not connection.closed:
                    try:
                        connection.invalidate()
                    finally:
                        connection.close()
        except SQLAlchemyError:
            raise TelemetryError("ownership_unavailable") from None
        finally:
            if self._engine is not None:
                try:
                    self._engine.dispose()
                except SQLAlchemyError:
                    raise TelemetryError("ownership_unavailable") from None
                finally:
                    self._engine = None
