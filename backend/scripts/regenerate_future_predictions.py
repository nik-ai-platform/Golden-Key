import argparse
import json
import logging
from datetime import datetime, timezone

from app.database.session import SessionLocal
from app.models.game import Game
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.services.odds_service import NoCompleteOddsSnapshotError
from app.services.prediction_engine import PredictionEngine
from app.services.prediction_publication import canonical_prediction_id_query


logger = logging.getLogger(__name__)
STATES = ("revised", "reused", "protected", "ineligible", "no_odds", "failed")


def regenerate_future_predictions(db, game_ids: list[int]) -> dict:
    requested_ids = list(dict.fromkeys(game_ids))
    engine = PredictionEngine()
    results = []

    for game_id in requested_ids:
        try:
            game = (
                db.query(Game).filter(Game.id == game_id)
                .populate_existing().with_for_update().first()
            )
            if game is None:
                db.rollback()
                results.append({"game_id": game_id, "status": "ineligible", "reason": "not_found"})
                continue
            existing_ids = set(db.scalars(canonical_prediction_id_query([game_id])))
            settled = (
                db.query(PredictionResult.id)
                .join(Prediction, Prediction.id == PredictionResult.prediction_id)
                .filter(Prediction.game_id == game_id).first()
            ) is not None
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if game.status == "final" or game.game_date <= now or settled:
                db.rollback()
                results.append({
                    "game_id": game_id, "status": "protected",
                    "prediction_ids": sorted(existing_ids),
                })
                continue
            if game.status != "scheduled":
                db.rollback()
                results.append({"game_id": game_id, "status": "ineligible", "reason": "not_scheduled"})
                continue
            # Normal refresh is retry-safe after partial success; never force
            # another stochastic revision for already completed identical inputs.
            predictions = engine.analyze_markets(db=db, game_id=game_id, persist=True)
            prediction_ids = {prediction.id for prediction in predictions}
            results.append({
                "game_id": game_id,
                "status": "revised" if prediction_ids != existing_ids else "reused",
                "prediction_ids": sorted(prediction_ids),
            })
        except NoCompleteOddsSnapshotError:
            db.rollback()
            logger.warning("Prediction refresh unavailable for game %s: no complete odds", game_id)
            results.append({
                "game_id": game_id, "status": "no_odds",
                "error_type": "NoCompleteOddsSnapshotError", "message": "No complete odds snapshot",
            })
        except Exception as error:
            db.rollback()
            error_type = type(error).__name__
            logger.error("Prediction refresh failed for game %s (%s)", game_id, error_type)
            results.append({
                "game_id": game_id, "status": "failed",
                "error_type": error_type, "message": "Prediction refresh failed; transaction rolled back",
            })

    counts = {state: sum(row["status"] == state for row in results) for state in STATES}
    return {"counts": counts, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Retry-safe refresh of eligible future system predictions by game id.",
    )
    parser.add_argument(
        "--game-id",
        type=int,
        action="append",
        required=True,
        dest="game_ids",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        results = regenerate_future_predictions(db, args.game_ids)
        print(json.dumps(results, indent=2))
    return int(bool(results["counts"]["failed"] or results["counts"]["no_odds"]))


if __name__ == "__main__":
    raise SystemExit(main())