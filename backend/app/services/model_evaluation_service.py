from app.schemas.model_evaluation import ModelComparison
from app.schemas.model_evaluation import ModelMetric


class ModelEvaluationService:
    """Evaluates model metrics and recommends promotions from objective rules."""

    def __init__(self, min_sample_size: int = 100):
        self.min_sample_size = min_sample_size

    def evaluate_model(self, model_version, games):
        replay = self.historical_replay(model_version, games)
        if not replay:
            return ModelMetric(
                accuracy=0.0,
                calibration=0.0,
                average_confidence=0.0,
                predictions=0,
            )

        total = len(replay)
        correct = sum(1 for item in replay if item["correct"])
        confidences = [item["confidence"] for item in replay]

        # Calibration error as mean absolute gap between confidence and observed 0/100 outcome.
        calibration_errors = [
            abs(item["confidence"] - (100.0 if item["correct"] else 0.0))
            for item in replay
        ]

        return ModelMetric(
            accuracy=round((correct / total) * 100.0, 2),
            calibration=round(sum(calibration_errors) / total, 2),
            average_confidence=round(sum(confidences) / total, 2),
            predictions=total,
        )

    def compare_models(self, current, candidate):
        current_metric = self._to_metric(current)
        candidate_metric = self._to_metric(candidate)

        comparison = ModelComparison(
            current_model=current_metric,
            candidate_model=candidate_metric,
            winner="current",
        )
        comparison.winner = self.recommend_model(comparison)
        return comparison

    def recommend_model(self, comparison):
        candidate = comparison.candidate_model
        current = comparison.current_model

        enough_samples = candidate.predictions >= self.min_sample_size
        better_accuracy = candidate.accuracy > current.accuracy
        not_worse_calibration = candidate.calibration <= current.calibration

        if enough_samples and better_accuracy and not_worse_calibration:
            return "candidate"

        return "current"

    def historical_replay(self, model_version, games):
        replay = []

        for game in games or []:
            actual_winner = self._read(game, ("actual_winner", "winner", "actual"))
            predicted = self._prediction_for_model(game, model_version)

            if actual_winner is None or predicted["winner"] is None:
                continue

            replay.append(
                {
                    "actual_winner": str(actual_winner),
                    "predicted_winner": str(predicted["winner"]),
                    "confidence": predicted["confidence"],
                    "correct": str(predicted["winner"]) == str(actual_winner),
                }
            )

        return replay

    def _prediction_for_model(self, game, model_version):
        predictions = self._read(game, ("predictions",))
        if isinstance(predictions, dict) and model_version in predictions:
            version_payload = predictions[model_version]
            if isinstance(version_payload, dict):
                winner = version_payload.get("winner")
                confidence = float(version_payload.get("confidence", 50.0) or 50.0)
                return {"winner": winner, "confidence": round(confidence, 2)}

            return {"winner": version_payload, "confidence": 50.0}

        winner = self._read(
            game,
            (
                f"{model_version}_winner",
                "predicted_winner",
                "prediction",
                "winner",
            ),
        )
        confidence = self._read(
            game,
            (
                f"{model_version}_confidence",
                "predicted_confidence",
                "confidence",
            ),
        )

        return {
            "winner": winner,
            "confidence": round(float(confidence if confidence is not None else 50.0), 2),
        }

    def _read(self, obj, keys):
        if isinstance(obj, dict):
            for key in keys:
                if key in obj:
                    return obj[key]
            return None

        for key in keys:
            if hasattr(obj, key):
                return getattr(obj, key)

        return None

    def _to_metric(self, value):
        if isinstance(value, ModelMetric):
            return value

        if isinstance(value, dict):
            return ModelMetric(**value)

        return ModelMetric(
            accuracy=round(float(getattr(value, "accuracy", 0.0) or 0.0), 2),
            calibration=round(float(getattr(value, "calibration", 0.0) or 0.0), 2),
            average_confidence=round(float(getattr(value, "average_confidence", 0.0) or 0.0), 2),
            predictions=int(getattr(value, "predictions", getattr(value, "total_predictions", 0)) or 0),
        )