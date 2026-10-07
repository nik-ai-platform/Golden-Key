from __future__ import annotations

import logging
import os
import sys
import time

from app.database.session import SessionLocal
from app.services.odds_service import NoCompleteOddsSnapshotError
from app.services.ncaaf_shadow_collection_service import (
    collect_ncaaf_shadow_evidence,
)
from app.services.prediction_engine import PredictionEngine
from app.workers.game_importer import GameOddsImporter
from app.workers.worker_instrumentation import WorkerInstrumentation, worker_cycle

logger = logging.getLogger(__name__)

DEFAULT_SPORTS = (
    "NFL",
    "NBA",
    "NCAAF",
    "NCAAB",
    "WNBA",
)

DEFAULT_POLL_SECONDS = 3600
MINIMUM_POLL_SECONDS = 300


def _configured_sports() -> tuple[str, ...]:
    raw = os.getenv("UPCOMING_GAME_SPORTS", "")

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
        "UPCOMING_GAME_POLL_SECONDS",
        str(DEFAULT_POLL_SECONDS),
    )

    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_POLL_SECONDS

    return max(value, MINIMUM_POLL_SECONDS)


def run_once() -> dict[str, dict[str, int | str]]:
    with worker_cycle(
        "upcoming-game-worker", _configured_sports(), _poll_seconds(), "after_completion",
    ) as telemetry:
        return _run_once(telemetry)


def _run_once(telemetry: WorkerInstrumentation) -> dict[str, dict[str, int | str]]:
    results: dict[str, dict[str, int | str]] = {}

    for sport in _configured_sports():
        db = None
        importer = None
        original_fetch = None
        imported_count = 0
        import_errors = 0
        predictions_generated = 0
        predictions_skipped_no_odds = 0
        prediction_errors = 0

        try:
            db = SessionLocal()
            telemetry.business_session_opened()
            importer = GameOddsImporter(db=db)
            if telemetry.enabled:
                original_fetch = importer.live_data.fetch_games
                importer.live_data.fetch_games = telemetry.wrap_fetch(sport, original_fetch)
            games = importer.import_games(sport)
            imported_count = len(games)
            engine = PredictionEngine()
            sources_by_game = {
                game_id: source
                for source in importer.source_imports
                for game_id in source.game_ids
            }

            for game in games:
                source = sources_by_game.get(game.id)
                try:
                    predictions = engine.analyze_markets(
                        db=db,
                        game_id=game.id,
                        persist=True,
                    )
                    predictions_generated += len(predictions)
                    if source is not None:
                        source.predictions += len(predictions)
                        telemetry.observed_game(sport, source.provider_source)
                except NoCompleteOddsSnapshotError:
                    predictions_skipped_no_odds += 1
                    if source is not None:
                        source.predictions_skipped_no_odds += 1
                    logger.info(
                        (
                            "Prediction skipped: no complete odds snapshot "
                            "sport=%s game_id=%s"
                        ),
                        sport,
                        game.id,
                    )
                except Exception:
                    db.rollback()
                    prediction_errors += 1
                    if source is not None:
                        source.errors += 1
                        telemetry.observed_game(sport, source.provider_source, failed=True)
                    logger.exception(
                        "Prediction generation failed sport=%s game_id=%s",
                        sport,
                        game.id,
                    )

        except Exception:
            import_errors += 1
            if db is not None:
                db.rollback()

            logger.exception(
                "Upcoming game import failed for %s",
                sport,
            )

        finally:
            interrupted = sys.exc_info()[0] is not None
            if interrupted:
                telemetry.begin_cleanup()
            if importer is not None:
                for source in importer.source_imports:
                    logger.info(
                        "Upcoming competition sync sport=%s provider_source=%s league=%s "
                        "fetched=%s processed=%s created=%s refreshed=%s usable_odds=%s "
                        "skipped_no_odds=%s predictions=%s predictions_skipped_no_odds=%s "
                        "errors=%s game_date_min=%s game_date_max=%s",
                        sport, source.provider_source, source.league,
                        source.fetched, source.processed, source.created, source.refreshed,
                        source.usable_odds, source.skipped_no_odds, source.predictions,
                        source.predictions_skipped_no_odds, source.errors,
                        source.game_date_min, source.game_date_max,
                    )
            if original_fetch is not None:
                importer.live_data.fetch_games = original_fetch
            if db is not None:
                try:
                    db.close()
                except BaseException:
                    telemetry.begin_cleanup()
                    raise
                telemetry.business_session_closed()
            if telemetry.enabled and importer is not None:
                for summary in importer.source_imports:
                    identity = telemetry.source(sport, summary.provider_source)
                    if identity is None or identity not in telemetry.evidence:
                        continue
                    evidence = telemetry.evidence[identity]
                    counters = {"errors": summary.errors}
                    if evidence.fetched:
                        counters.update({
                            "fetched": summary.fetched, "processed": summary.processed,
                            "created": summary.created, "refreshed": summary.refreshed,
                            "usable_odds": summary.usable_odds, "skipped_no_odds": summary.skipped_no_odds,
                        })
                        if not import_errors:
                            counters.update({
                                "prediction_rows_returned": summary.predictions,
                                "publications_skipped": summary.predictions_skipped_no_odds,
                            })
                    timestamps = {
                        key: value for key, value in (
                            ("game_date_min", summary.game_date_min),
                            ("game_date_max", summary.game_date_max),
                        ) if value is not None
                    }
                    telemetry.update_source(
                        identity, counters=counters, timestamps=timestamps,
                        error_code="invalid_source_data" if summary.errors else None,
                    )
                    if not interrupted and not (import_errors and not summary.errors):
                        telemetry.finish_source(
                            identity, failed=bool(summary.errors and not summary.processed),
                        )
            telemetry.flush_sport(sport)

        if sport == "NCAAF":
            try:
                collect_ncaaf_shadow_evidence()
            except Exception:
                logger.exception("NCAAF shadow collection hook failed")
                telemetry.auxiliary_failed()

        results[sport] = {
            "sport": sport,
            "imported": imported_count,
            "predictions_generated": predictions_generated,
            "predictions_skipped_no_odds": predictions_skipped_no_odds,
            "prediction_errors": prediction_errors,
        }

        logger.info(
            (
                "Upcoming game sync sport=%s imported=%s import_errors=%s "
                "predictions_generated=%s predictions_skipped_no_odds=%s "
                "prediction_errors=%s"
            ),
            sport,
            imported_count,
            import_errors,
            predictions_generated,
            predictions_skipped_no_odds,
            prediction_errors,
        )

    return results


def run_forever() -> None:
    poll_seconds = _poll_seconds()

    logger.info(
        "Starting upcoming-game worker sports=%s poll_seconds=%s",
        ",".join(_configured_sports()),
        poll_seconds,
    )

    with WorkerInstrumentation(
        "upcoming-game-worker", _configured_sports(), poll_seconds, "after_completion",
    ).process():
        while True:
            try:
                run_once()
            except Exception:
                logger.exception("Unexpected upcoming-game worker cycle failure")

            time.sleep(poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    run_forever()