from __future__ import annotations

import logging
import os
import time

from app.database.session import SessionLocal
from app.services.prediction_engine import PredictionEngine
from app.workers.game_importer import GameOddsImporter

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
    results: dict[str, dict[str, int | str]] = {}

    for sport in _configured_sports():
        db = None
        imported_count = 0
        predictions_generated = 0
        prediction_errors = 0

        try:
            db = SessionLocal()
            importer = GameOddsImporter(db=db)
            games = importer.import_games(sport)
            imported_count = len(games)
            engine = PredictionEngine()

            for game in games:
                try:
                    predictions = engine.analyze_markets(
                        db=db,
                        game_id=game.id,
                        persist=True,
                    )
                    predictions_generated += len(predictions)
                except Exception:
                    db.rollback()
                    prediction_errors += 1
                    logger.exception(
                        "Prediction generation failed sport=%s game_id=%s",
                        sport,
                        game.id,
                    )

        except Exception:
            if db is not None:
                db.rollback()

            logger.exception(
                "Upcoming game import failed for %s",
                sport,
            )

        finally:
            if db is not None:
                db.close()

        results[sport] = {
            "sport": sport,
            "imported": imported_count,
            "predictions_generated": predictions_generated,
            "prediction_errors": prediction_errors,
        }

        logger.info(
            (
                "Upcoming game sync sport=%s imported=%s "
                "predictions_generated=%s prediction_errors=%s"
            ),
            sport,
            imported_count,
            predictions_generated,
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