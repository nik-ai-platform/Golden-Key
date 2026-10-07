from contextlib import contextmanager
from dataclasses import dataclass
import math
from threading import Lock
from typing import Generator

from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool


class TelemetryError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Telemetry operation failed: {code}")


@dataclass(frozen=True)
class TelemetryConfig:
    enabled: bool = False
    statement_timeout_ms: int = 500
    lock_timeout_ms: int = 100
    pool_timeout_seconds: float = 0.2
    connect_timeout_seconds: int = 2

    def __post_init__(self) -> None:
        if (
            type(self.enabled) is not bool
            or type(self.statement_timeout_ms) is not int or not 50 <= self.statement_timeout_ms <= 5000
            or type(self.lock_timeout_ms) is not int or not 10 <= self.lock_timeout_ms <= 1000
            or type(self.connect_timeout_seconds) is not int or not 1 <= self.connect_timeout_seconds <= 10
            or type(self.pool_timeout_seconds) not in {int, float}
            or not math.isfinite(self.pool_timeout_seconds) or not 0.01 <= self.pool_timeout_seconds <= 2
        ):
            raise TelemetryError("invalid_configuration")


def _settings():
    try:
        from app.core.config import settings
    except ValidationError:
        raise TelemetryError("invalid_configuration") from None
    return settings


class TelemetryDatabase:
    """Owns only telemetry connections; initialization never opens a connection."""

    def __init__(self, url: str | None = None, config: TelemetryConfig | None = None) -> None:
        self._url = url
        self._config = config
        self._engine: Engine | None = None
        self._factory: sessionmaker[Session] | None = None
        self._lock = Lock()

    @property
    def config(self) -> TelemetryConfig:
        if self._config is None:
            settings = _settings()
            self._config = TelemetryConfig(
                enabled=settings.OPERATIONS_TELEMETRY_ENABLED,
                statement_timeout_ms=settings.OPERATIONS_TELEMETRY_STATEMENT_TIMEOUT_MS,
                lock_timeout_ms=settings.OPERATIONS_TELEMETRY_LOCK_TIMEOUT_MS,
                pool_timeout_seconds=settings.OPERATIONS_TELEMETRY_POOL_TIMEOUT_SECONDS,
                connect_timeout_seconds=settings.OPERATIONS_TELEMETRY_CONNECT_TIMEOUT_SECONDS,
            )
        return self._config

    @property
    def engine(self) -> Engine:
        if not self.config.enabled:
            raise TelemetryError("disabled")
        with self._lock:
            if self._engine is None:
                if self._url is None:
                    self._url = _settings().DATABASE_URL
                dialect = make_url(self._url).get_backend_name()
                if dialect not in {"postgresql", "sqlite"}:
                    raise TelemetryError("unsupported_database")
                options: dict = {}
                if dialect == "postgresql":
                    options = {
                        "connect_timeout": self.config.connect_timeout_seconds,
                        "options": (
                            f"-c statement_timeout={self.config.statement_timeout_ms} "
                            f"-c lock_timeout={self.config.lock_timeout_ms} -c timezone=UTC"
                        ),
                    }
                elif dialect == "sqlite":
                    options = {"check_same_thread": False, "timeout": self.config.pool_timeout_seconds}
                self._engine = create_engine(
                    self._url, poolclass=QueuePool, pool_size=1, max_overflow=0,
                    pool_timeout=self.config.pool_timeout_seconds, connect_args=options,
                    hide_parameters=True,
                )
                if dialect == "sqlite":
                    event.listen(self._engine, "connect", _sqlite_foreign_keys)
                self._factory = sessionmaker(bind=self._engine, autoflush=False, expire_on_commit=False)
            return self._engine

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        try:
            self.engine
            if self._factory is None:
                raise TelemetryError("storage_unavailable")
            with self._factory() as session:
                with session.begin():
                    yield session
        except SQLAlchemyError:
            raise TelemetryError("storage_unavailable") from None

    def dispose(self) -> None:
        with self._lock:
            if self._engine is not None:
                self._engine.dispose()
            self._engine = None
            self._factory = None


def _sqlite_foreign_keys(connection, _record) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


telemetry_database = TelemetryDatabase()
