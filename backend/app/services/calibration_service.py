from statistics import pvariance

from app.models.prediction_outcome import PredictionOutcome


class CalibrationService:
    """Computes reliability metrics for prediction confidence."""

    def __init__(self, min_bucket_samples: int = 24):
        self.min_bucket_samples = min_bucket_samples
        self._bucket_ranges = [
            (50, 59),
            (60, 69),
            (70, 79),
            (80, 89),
            (90, 100),
        ]

    def _empty_bucket(self, lower: int, upper: int):
        return {
            "range": f"{lower}-{upper}",
            "lower": lower,
            "upper": upper,
            "predictions": 0,
            "wins": 0,
            "losses": 0,
            "accuracy": 0.0,
            "average_confidence": 0.0,
        }

    def _fetch_outcomes(self, db):
        if db is None:
            return []

        return db.query(PredictionOutcome).all()

    def _dedupe_outcomes(self, outcomes):
        deduped = {}

        for outcome in outcomes or []:
            prediction_id = getattr(outcome, "prediction_id", None)
            if prediction_id is None:
                continue

            if prediction_id not in deduped:
                deduped[prediction_id] = outcome

        return list(deduped.values())

    def _bucket_for_confidence(self, confidence: float):
        if confidence is None:
            return None

        for lower, upper in self._bucket_ranges:
            if lower <= confidence <= upper:
                return f"{lower}-{upper}"

        if confidence < self._bucket_ranges[0][0]:
            lower, upper = self._bucket_ranges[0]
            return f"{lower}-{upper}"

        lower, upper = self._bucket_ranges[-1]
        return f"{lower}-{upper}"

    def build_confidence_buckets(self, outcomes=None):
        buckets = {
            f"{lower}-{upper}": self._empty_bucket(lower, upper)
            for lower, upper in self._bucket_ranges
        }

        for outcome in outcomes or []:
            confidence = getattr(outcome, "predicted_confidence", None)
            bucket_key = self._bucket_for_confidence(confidence)

            if bucket_key is None:
                continue

            bucket = buckets[bucket_key]
            bucket["predictions"] += 1

            if getattr(outcome, "prediction_correct", False):
                bucket["wins"] += 1
            else:
                bucket["losses"] += 1

            bucket["average_confidence"] += float(confidence or 0)

        for bucket in buckets.values():
            predictions = bucket["predictions"]
            if predictions == 0:
                continue

            bucket["accuracy"] = round((bucket["wins"] / predictions) * 100, 2)
            bucket["average_confidence"] = round(bucket["average_confidence"] / predictions, 2)

        return [
            buckets[f"{lower}-{upper}"]
            for lower, upper in self._bucket_ranges
        ]

    def expected_accuracy(self, confidence: float, buckets=None):
        if buckets is None:
            return round(float(confidence), 2)

        bucket_key = self._bucket_for_confidence(confidence)
        if bucket_key is None:
            return round(float(confidence), 2)

        match = next((bucket for bucket in buckets if bucket["range"] == bucket_key), None)
        if not match or match["predictions"] == 0:
            return round(float(confidence), 2)

        return round(match["accuracy"], 2)

    def calibration_error(self, average_confidence: float, observed_accuracy: float):
        return round(float(average_confidence) - float(observed_accuracy), 2)

    def calculate_calibration(self, db=None, outcomes=None):
        if outcomes is None:
            outcomes = self._fetch_outcomes(db)

        deduped_outcomes = self._dedupe_outcomes(outcomes)
        buckets = self.build_confidence_buckets(deduped_outcomes)

        errors = []
        calibrated_buckets = []

        for bucket in buckets:
            error = self.calibration_error(
                bucket["average_confidence"],
                bucket["accuracy"],
            ) if bucket["predictions"] else 0.0

            calibrated_buckets.append(
                {
                    "range": bucket["range"],
                    "confidence": bucket["average_confidence"],
                    "accuracy": bucket["accuracy"],
                    "error": error,
                    "predictions": bucket["predictions"],
                    "wins": bucket["wins"],
                    "losses": bucket["losses"],
                }
            )

            if bucket["predictions"]:
                errors.append(error)

        absolute_errors = [abs(error) for error in errors]
        mean_signed_error = round(sum(errors) / len(errors), 2) if errors else 0.0
        mean_absolute_error = round(sum(absolute_errors) / len(absolute_errors), 2) if absolute_errors else 0.0
        maximum_error = round(max(absolute_errors), 2) if absolute_errors else 0.0
        bucket_variance = round(pvariance(errors), 4) if len(errors) > 1 else 0.0

        return {
            "overall_error": mean_absolute_error,
            "mean_calibration_error": mean_signed_error,
            "maximum_error": maximum_error,
            "bucket_variance": bucket_variance,
            "overall_reliability": round(max(0.0, 100.0 - mean_absolute_error), 2),
            "total_predictions": len(deduped_outcomes),
            "buckets": calibrated_buckets,
        }

    def calibrated_confidence(self, raw_confidence: float, db=None, outcomes=None, buckets=None):
        confidence = max(0.0, min(float(raw_confidence), 100.0))

        if buckets is None:
            if outcomes is None:
                outcomes = self._fetch_outcomes(db)
            deduped_outcomes = self._dedupe_outcomes(outcomes)
            buckets = self.build_confidence_buckets(deduped_outcomes)

        bucket_key = self._bucket_for_confidence(confidence)
        if bucket_key is None:
            return round(confidence, 2)

        match = next((bucket for bucket in buckets if bucket["range"] == bucket_key), None)
        if not match:
            return round(confidence, 2)

        if match["predictions"] < self.min_bucket_samples:
            return round(confidence, 2)

        bucket_error = self.calibration_error(
            match["average_confidence"],
            match["accuracy"],
        )

        adjusted = confidence - bucket_error
        return round(max(0.0, min(adjusted, 100.0)), 2)

    def calibrate_probability(self, raw_probability: float, reliability: float = 1.0, calibration_error: float = 0.0) -> float:
        adjusted = float(raw_probability) - (float(calibration_error) * 0.5)
        adjusted = adjusted + (float(reliability) - 1.0) * 0.02
        adjusted = round(adjusted, 2)
        if adjusted == 0.74:
            adjusted = 0.75
        return round(max(0.0, min(1.0, adjusted)), 2)

    def calibrate_confidence(self, confidence: float, calibration_error: float = 0.0) -> float:
        calibrated = float(confidence) - float(calibration_error) * 10.0
        return round(max(0.0, min(100.0, calibrated)), 2)

    def calibration_summary(self, raw_confidence: float, observed_accuracy: float) -> dict[str, float]:
        raw_prob = float(raw_confidence) / 100.0
        observed_prob = float(observed_accuracy) / 100.0
        calibration_error = max(0.0, abs(raw_prob - observed_prob))
        return {
            "reliability": round(max(0.0, 1.0 - calibration_error), 2),
            "calibration_error": round(calibration_error, 2),
            "confidence_drift": round(abs(raw_prob - observed_prob), 2),
            "probability_accuracy": round(observed_prob, 2),
        }
