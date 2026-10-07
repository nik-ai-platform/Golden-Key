from __future__ import annotations

import logging
import os
import sys
import time
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.services.final_score_settlement_service import (
    FinalScoreSettlementService,
    FinalScoreSyncSummary,
)
from app.services.sport_mapping_service import CompetitionSource
from app.services.ncaaf_shadow_collection_service import (
    settle_ncaaf_shadow_evidence,
)
from app.services.odds_provider_client import OddsProviderClient
from app.workers.worker_instrumentation import WorkerInstrumentation, worker_cycle

logger = logging.getLogger(__name__)

DEFAULT_SPORTS = (
    "NFL",
    "NBA",
    "NCAAF",
    "NCAAB",
    "WNBA",
)

DEFAULT_POLL_SECONDS = 900


class _ObservedSettlementService(FinalScoreSettlementService):
    def __init__(self, telemetry: WorkerInstrumentation, **kwargs) -> None:
        super().__init__(**kwargs)
        self.telemetry = telemetry

    def _sync_source(
        self, db: Session, internal_sport: str, source: CompetitionSource, days_from: int,
    ) -> FinalScoreSyncSummary:
        identity = self.telemetry.source(internal_sport, source.provider_key)
        if identity is not None:
            self.telemetry.start_source(identity)
        try:
            summary = super()._sync_source(db, internal_sport, source, days_from)
        except Exception:
            if identity is not None:
                self.telemetry.update_source(identity, counters={"errors": 1}, error_code="provider_unavailable")
                self.telemetry.finish_source(identity, failed=True)
            raise
        if identity is not None:
            self.telemetry.update_source(
                identity,
                counters={
                    key: getattr(summary, key)
                    for key in (
                        "fetched", "matched", "finalized", "already_final",
                        "unmatched", "skipped_not_final", "errors",
                    )
                } | {"games_settled": summary.settled},
                error_code="settlement_failed" if summary.errors else None,
            )
            if summary.finalized or summary.already_final:
                self.telemetry.observed_source_processing(identity)
            self.telemetry.finish_source(
                identity,
                failed=bool(summary.errors and not (summary.matched or summary.unmatched or summary.skipped_not_final)),
            )
        return summary


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
    with worker_cycle(
        "final-score-worker", _configured_sports(), _poll_seconds(), "start_to_start",
    ) as telemetry:
        return _run_once(telemetry)


def _run_once(telemetry: WorkerInstrumentation) -> dict[str, dict[str, int | str]]:
    results: dict[str, dict[str, int | str]] = {}

    for sport in _configured_sports():
        db = SessionLocal()
        telemetry.business_session_opened()

        try:
            if telemetry.enabled:
                service = _ObservedSettlementService(
                    telemetry, provider_client=OddsProviderClient(),
                )
            else:
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
            if sys.exc_info()[0] is not None:
                telemetry.begin_cleanup()
            try:
                db.close()
            except BaseException:
                telemetry.begin_cleanup()
                raise
            telemetry.business_session_closed()
            telemetry.flush_sport(sport)

        if sport == "NCAAF":
            try:
                settle_ncaaf_shadow_evidence()
            except Exception:
                logger.exception("NCAAF shadow settlement hook failed")
                telemetry.auxiliary_failed()

    return results


def run_forever() -> None:
    poll_seconds = _poll_seconds()

    logger.info(
        "Starting final-score worker sports=%s poll_seconds=%s",
        ",".join(_configured_sports()),
        poll_seconds,
    )

    with WorkerInstrumentation(
        "final-score-worker", _configured_sports(), poll_seconds, "start_to_start",
    ).process():
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