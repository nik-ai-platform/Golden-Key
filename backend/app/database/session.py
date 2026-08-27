from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker
from time import perf_counter

from app.core.config import settings
from app.services.performance_metrics_service import performance_metrics


engine_kwargs = {}

# Queue pool tuning prevents connection starvation under concurrent load.
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT_SECONDS,
        "pool_recycle": settings.DB_POOL_RECYCLE_SECONDS,
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
    }

engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)


@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(perf_counter())


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    started_at = conn.info.setdefault("query_start_time", []).pop(-1)
    performance_metrics.record_db_query_latency((perf_counter() - started_at) * 1000)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
