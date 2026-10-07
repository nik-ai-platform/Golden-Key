"""Standalone bounded retention scheduling, never started by the API."""

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json
import logging
import threading

from app.database.telemetry_session import TelemetryDatabase, TelemetryError, telemetry_database
from app.services.worker_telemetry_service import PruneSummary, WorkerTelemetryService


logger = logging.getLogger(__name__)


def run_retention(
    *, interval_seconds: int = 3600, retention_days: int = 30, batch_size: int = 500,
    dry_run: bool = True, once: bool = False,
    database: TelemetryDatabase = telemetry_database,
    stop: threading.Event | None = None,
) -> int:
    if not 60 <= interval_seconds <= 86400 or not 1 <= retention_days <= 365 or not 1 <= batch_size <= 500:
        raise ValueError("Retention settings outside supported bounds")
    event = stop if stop is not None else threading.Event()
    service = WorkerTelemetryService(database)
    try:
        while not event.is_set():
            try:
                summary = service.prune_history(
                    at=datetime.now(UTC), retention_days=retention_days,
                    batch_size=batch_size, dry_run=dry_run,
                )
            except TelemetryError as error:
                logger.error("Telemetry retention failed code=%s", error.code)
                if once:
                    return 1
            else:
                logger.info("Telemetry retention summary %s", json.dumps(asdict(summary), sort_keys=True))
                if summary.enabled and not summary.lock_acquired:
                    logger.warning("Telemetry retention skipped code=cleanup_lock_busy")
                if once:
                    return exit_code(summary)
            event.wait(interval_seconds)
        return 0
    finally:
        database.dispose()


def exit_code(summary: PruneSummary) -> int:
    return 2 if summary.enabled and not summary.lock_acquired else 0


def main(argv: list[str] | None = None) -> int:
    from app.core.config import settings

    parser = argparse.ArgumentParser(description="Run one bounded retention batch per interval; dry-run by default.")
    parser.add_argument("--interval-seconds", type=int, default=3600)
    parser.add_argument("--retention-days", type=int, default=settings.OPERATIONS_CYCLE_RETENTION_DAYS)
    parser.add_argument("--batch-size", type=int, default=500)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true", help="Explicitly permit eligible telemetry history deletion")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if not 60 <= args.interval_seconds <= 86400 or not 1 <= args.retention_days <= 365 or not 1 <= args.batch_size <= 500:
        parser.error("interval must be 60..86400, retention 1..365, batch size 1..500")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        return run_retention(
            interval_seconds=args.interval_seconds, retention_days=args.retention_days,
            batch_size=args.batch_size, dry_run=not args.apply, once=args.once,
        )
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
