"""Explicit bounded cleanup; never scheduled or invoked by an HTTP request."""

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json

from pydantic import ValidationError

from app.database.telemetry_session import TelemetryError, telemetry_database
from app.services.worker_telemetry_service import WorkerTelemetryService


def main(argv: list[str] | None = None) -> int:
    try:
        from app.core.config import settings
    except ValidationError:
        print(json.dumps({"error": "invalid_configuration"}, sort_keys=True))
        return 1

    parser = argparse.ArgumentParser(description="Prune one bounded batch of eligible worker telemetry.")
    parser.add_argument("--retention-days", type=int, default=settings.OPERATIONS_CYCLE_RETENTION_DAYS)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.retention_days <= 365 or not 1 <= args.batch_size <= 500:
        parser.error("retention-days must be 1..365 and batch-size must be 1..500")
    try:
        summary = WorkerTelemetryService().prune_history(
            at=datetime.now(UTC), retention_days=args.retention_days,
            batch_size=args.batch_size, dry_run=args.dry_run,
        )
        print(json.dumps(asdict(summary), sort_keys=True))
        return 0 if not summary.enabled or summary.lock_acquired else 2
    except TelemetryError as error:
        print(json.dumps({"error": error.code}, sort_keys=True))
        return 1
    finally:
        telemetry_database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
