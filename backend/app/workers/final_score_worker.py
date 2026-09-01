from __future__ import annotations

import logging
import os
import time

from app.database.session import SessionLocal
from app.services.final_score_settlement_service import (
    FinalScoreSettlementService,
)
from app.services.odds_provider_client import OddsProviderClient

logger = logging.getLogger(__name__)

DEFAULT_SPORTS = (
    "NFL",
    "NBA",
    "NCAAF",
    "NCAAB",
    "WNBA",
)

DEFAULT_POLL_SECONDS = 900


def _configured_sports() -> tuple[str, ...]:
    raw = os.getenv("FINAL_SCORE_SPORTS", "")

    if not raw.strip():
        return DEFAULT_SPORTS

    sports = tuple(
        item.strip().upper()
        for item in raw.split(",")
        if item.strip()
    )

    return sports or DEFAULT_SPORTS


def _poll_seconds() -> int:
    raw = os.getenv(
        "FINAL_SCORE_POLL_SECONDS",
        str(DEFAULT_POLL_SECONDS),
    )

    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_POLL_SECONDS

    return max(value, 60)


def run_once() -> dict[str, dict[str, int | str]]:
    results: dict[str, dict[str, int | str]] = {}

    for sport in _configured_sports():
        db = SessionLocal()

        try:
            service = FinalScoreSettlementService(
                provider_client=OddsProviderClient(),
            )

            summary = service.sync_sport(
                db,
                sport,
                days_from=3,
            )

            results[sport] = {
                "sport": summary.sport,
                "fetched": summary.fetched,
                "matched": summary.matched,
                "finalized": summary.finalized,
                "already_final": summary.already_final,
                "unmatched": summary.unmatched,
                "skipped_not_final": summary.skipped_not_final,
                "settled": summary.settled,
                "errors": summary.errors,
            }

            logger.info(
                (
                    "Final score sync sport=%s "
                    "fetched=%s matched=%s finalized=%s "
                    "already_final=%s unmatched=%s "
                    "skipped_not_final=%s settled=%s errors=%s"
                ),
                summary.sport,
                summary.fetched,
                summary.matched,
                summary.finalized,
                summary.already_final,
                summary.unmatched,
                summary.skipped_not_final,
                summary.settled,
                summary.errors,
            )

        except Exception:
            db.rollback()

            results[sport] = {
                "sport": sport,
                "fetched": 0,
                "matched": 0,
                "finalized": 0,
                "already_final": 0,
                "unmatched": 0,
                "skipped_not_final": 0,
                "settled": 0,
                "errors": 1,
            }

            logger.exception(
                "Final score synchronization failed for %s",
                sport,
            )

        finally:
            db.close()

    return results


def run_forever() -> None:
    poll_seconds = _poll_seconds()

    logger.info(
        "Starting final-score worker sports=%s poll_seconds=%s",
        ",".join(_configured_sports()),
        poll_seconds,
    )

    while True:
        started = time.monotonic()

        run_once()

        elapsed = time.monotonic() - started
        sleep_seconds = max(poll_seconds - elapsed, 1)

        time.sleep(sleep_seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    run_forever()