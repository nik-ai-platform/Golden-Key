import argparse
import json
from datetime import datetime, timezone

from app.database.session import SessionLocal
from app.models.game import Game
from app.models.prediction_record import Prediction
from app.services.prediction_engine import PredictionEngine


def regenerate_future_predictions(db, game_ids: list[int]) -> list[dict]:
    requested_ids = list(dict.fromkeys(game_ids))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    games = (
        db.query(Game)
        .filter(
            Game.id.in_(requested_ids),
            Game.game_date > now,
            Game.status == "scheduled",
        )
        .order_by(Game.game_date.asc())
        .all()
    )
    games_by_id = {game.id: game for game in games}
    engine = PredictionEngine()
    results = []

    for game_id in requested_ids:
        game = games_by_id.get(game_id)
        if game is None:
            results.append({"game_id": game_id, "status": "ineligible"})
            continue

        existing_ids = {
            prediction.id
            for prediction in db.query(Prediction)
            .filter(Prediction.game_id == game.id)
            .all()
        }
        predictions = engine.analyze_markets(
            db=db,
            game_id=game.id,
            persist=True,
            force_regenerate=True,
        )
        prediction_ids = {prediction.id for prediction in predictions}
        results.append(
            {
                "game_id": game.id,
                "status": (
                    "regenerated"
                    if prediction_ids != existing_ids
                    else "protected_or_unchanged"
                ),
                "prediction_ids": sorted(prediction_ids),
            }
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate eligible future system predictions by game id.",
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


if __name__ == "__main__":
    main()