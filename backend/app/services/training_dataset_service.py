import csv
import io
from datetime import datetime

from app.models.feature_snapshot import FeatureSnapshot
from app.models.game import Game
from app.models.nik_score import NikScore
from app.models.prediction_outcome import PredictionOutcome


class TrainingDatasetService:
    """Builds reproducible training records from stored prediction-time features."""

    _REQUIRED_FIELDS = (
        "sport",
        "confidence",
        "winner",
        "correct",
        "model_version",
    )

    def __init__(self):
        self._latest_dataset = []

    def build_dataset(self, start_date, end_date, db=None):
        if db is None:
            raise ValueError("db is required to build dataset")

        outcomes = (
            db.query(PredictionOutcome)
            .filter(PredictionOutcome.created_at >= start_date)
            .filter(PredictionOutcome.created_at <= end_date)
            .order_by(PredictionOutcome.created_at.asc(), PredictionOutcome.id.asc())
            .all()
        )

        dataset = []

        for outcome in outcomes:
            prediction = (
                db.query(NikScore)
                .filter(NikScore.id == outcome.prediction_id)
                .first()
            )
            if prediction is None:
                continue

            game = (
                db.query(Game)
                .filter(Game.id == outcome.game_id)
                .first()
            )
            if game is None:
                continue

            feature_rows = (
                db.query(FeatureSnapshot)
                .filter(FeatureSnapshot.prediction_id == outcome.prediction_id)
                .order_by(FeatureSnapshot.feature_name.asc(), FeatureSnapshot.id.asc())
                .all()
            )
            if not feature_rows:
                continue

            features = {
                row.feature_name: float(row.feature_value)
                for row in feature_rows
            }

            record = {
                "sport": str(game.sport),
                "confidence": round(float(prediction.confidence or 0.0), 2),
                "winner": self._winner_label(game, outcome.actual_winner),
                "correct": bool(outcome.prediction_correct),
                "model_version": str(prediction.model_version or "unknown"),
                **features,
            }

            dataset.append(record)

        dataset.sort(
            key=lambda item: (
                item.get("model_version", ""),
                item.get("sport", ""),
                item.get("winner", ""),
                item.get("confidence", 0.0),
            )
        )

        self._latest_dataset = dataset
        return dataset

    def export_dataset(self, format="csv"):
        if format != "csv":
            raise ValueError("Only csv export is supported")

        validation = self.validate_dataset(self._latest_dataset)
        if not validation["valid"]:
            raise ValueError("Cannot export invalid dataset")

        if not self._latest_dataset:
            return ""

        common = list(self._REQUIRED_FIELDS)
        dynamic = sorted(
            {
                key
                for row in self._latest_dataset
                for key in row.keys()
                if key not in common
            }
        )
        fieldnames = common + dynamic

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in self._latest_dataset:
            writer.writerow(row)

        return buffer.getvalue()

    def validate_dataset(self, dataset):
        errors = []
        rows = dataset or []

        for index, row in enumerate(rows):
            missing = [field for field in self._REQUIRED_FIELDS if field not in row]
            if missing:
                errors.append(f"row {index}: missing fields {','.join(missing)}")
                continue

            if row["winner"] not in {"home", "away"}:
                errors.append(f"row {index}: winner must be home or away")

            if not isinstance(row["correct"], bool):
                errors.append(f"row {index}: correct must be bool")

            if not isinstance(row["sport"], str) or not row["sport"]:
                errors.append(f"row {index}: sport must be non-empty string")

            if not isinstance(row["model_version"], str) or not row["model_version"]:
                errors.append(f"row {index}: model_version must be non-empty string")

            for key, value in row.items():
                if key in {"sport", "winner", "correct", "model_version"}:
                    continue
                if not isinstance(value, (int, float)):
                    errors.append(f"row {index}: {key} must be numeric")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "records": len(rows),
        }

    def _winner_label(self, game: Game, actual_winner: str):
        winner = str(actual_winner or "").strip().lower()

        if game.home_team and winner == str(game.home_team.name).strip().lower():
            return "home"

        if game.away_team and winner == str(game.away_team.name).strip().lower():
            return "away"

        if winner in {"home", "away"}:
            return winner

        return "home"