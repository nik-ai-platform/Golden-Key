from sqlalchemy.orm import Session
from app.schemas.confidence_analytics import (
    ConfidenceAnalytics,
    ConfidenceBucket,
    ConfidenceCalibrationBucket,
)

from app.core.constants import CALIBRATION_50
from app.core.constants import CALIBRATION_60
from app.core.constants import CALIBRATION_70
from app.core.constants import CALIBRATION_80
from app.core.constants import CALIBRATION_90
from app.core.constants import HIGH_CONFIDENCE
from app.core.constants import LOW_CONFIDENCE
from app.core.constants import MAX_SCORE
from app.core.constants import MODERATE_CONFIDENCE
from app.repositories import analytics_repository


class ConfidenceService:
    """
    Handles confidence-related analysis.
    """


    def _get_evaluations(
        self,
        db: Session
    ):
        return analytics_repository.get_evaluations(db)


    def _bucket_name(
        self,
        confidence: float
    ):
        if confidence <= LOW_CONFIDENCE:
            return "LOW"

        if confidence <= MODERATE_CONFIDENCE:
            return "MODERATE"

        if confidence <= HIGH_CONFIDENCE:
            return "STRONG"

        return "ELITE"


    def get_bucket_statistics(
        self,
        db: Session
    ):
        evaluations = self._get_evaluations(db)

        grouped = {
            "LOW": [],
            "MODERATE": [],
            "STRONG": [],
            "ELITE": [],
        }

        for item in evaluations:
            grouped[self._bucket_name(item.confidence)].append(item)

        buckets = []

        for label in ["LOW", "MODERATE", "STRONG", "ELITE"]:
            values = grouped[label]

            if not values:
                buckets.append(
                    ConfidenceBucket(
                        label=label,
                        predictions=0,
                        accuracy=0,
                    )
                )
                continue

            correct = sum(
                1
                for value in values
                if value.correct
            )

            buckets.append(
                ConfidenceBucket(
                    label=label,
                    predictions=len(values),
                    accuracy=round(
                        correct /
                        len(values)
                        *
                        MAX_SCORE,
                        2,
                    ),
                )
            )

        return buckets


    def get_average_confidence(
        self,
        db: Session
    ):
        evaluations = self._get_evaluations(db)

        if not evaluations:
            return 0

        return round(
            sum(item.confidence for item in evaluations)
            /
            len(evaluations),
            2,
        )


    def get_confidence_distribution(
        self,
        db: Session
    ):
        evaluations = self._get_evaluations(db)

        if not evaluations:
            return ConfidenceAnalytics(
                average_confidence=0,
                highest_confidence=0,
                lowest_confidence=0,
                buckets=self.get_bucket_statistics(db),
            )

        confidences = [item.confidence for item in evaluations]

        return ConfidenceAnalytics(
            average_confidence=self.get_average_confidence(db),
            highest_confidence=max(confidences),
            lowest_confidence=min(confidences),
            buckets=self.get_bucket_statistics(db),
        )


    def get_confidence_history(
        self,
        db: Session
    ):
        evaluations = self._get_evaluations(db)

        if not evaluations:
            return []

        ordered = sorted(
            evaluations,
            key=lambda item: getattr(item, "created_at", None) or "",
        )

        history = []
        running_total = 0

        for index, item in enumerate(ordered, start=1):
            running_total += item.confidence

            entry = {
                "position": index,
                "confidence": item.confidence,
                "rolling_average": round(running_total / index, 2),
            }

            if getattr(item, "created_at", None) is not None:
                entry["timestamp"] = item.created_at.isoformat()

            history.append(entry)

        return history


    def get_confidence_calibration(
        self,
        db: Session,
        tolerance: float = 5.0,
    ):
        evaluations = self._get_evaluations(db)

        grouped = {
            "LOW": [],
            "MODERATE": [],
            "STRONG": [],
            "ELITE": [],
        }

        for item in evaluations:
            grouped[self._bucket_name(item.confidence)].append(item)

        comparisons = []

        for label in ["LOW", "MODERATE", "STRONG", "ELITE"]:
            values = grouped[label]

            if not values:
                comparisons.append(
                    ConfidenceCalibrationBucket(
                        label=label,
                        predictions=0,
                        predicted_confidence=0,
                        observed_accuracy=0,
                        calibration_gap=0,
                        well_calibrated=True,
                    )
                )
                continue

            predicted_confidence = round(
                sum(item.confidence for item in values)
                /
                len(values),
                2,
            )

            correct = sum(
                1
                for value in values
                if value.correct
            )

            observed_accuracy = round(
                correct /
                len(values)
                *
                MAX_SCORE,
                2,
            )

            calibration_gap = round(
                abs(predicted_confidence - observed_accuracy),
                2,
            )

            comparisons.append(
                ConfidenceCalibrationBucket(
                    label=label,
                    predictions=len(values),
                    predicted_confidence=predicted_confidence,
                    observed_accuracy=observed_accuracy,
                    calibration_gap=calibration_gap,
                    well_calibrated=calibration_gap <= tolerance,
                )
            )

        return comparisons


    def confidence_buckets(
        self,
        db: Session
    ):
        output = {}

        for bucket in self.get_bucket_statistics(db):
            output[bucket.label] = bucket.accuracy

        return output


    def calibration(
        self,
        db: Session
    ):
        evaluations = self._get_evaluations(db)


        buckets = {

            "0-50": [],

            "51-60": [],

            "61-70": [],

            "71-80": [],

            "81-90": [],

            "91-100": []

        }


        for evaluation in evaluations:

            confidence = (
                evaluation.confidence
            )


            if confidence <= CALIBRATION_50:
                buckets["0-50"].append(evaluation)

            elif confidence <= CALIBRATION_60:
                buckets["51-60"].append(evaluation)

            elif confidence <= CALIBRATION_70:
                buckets["61-70"].append(evaluation)

            elif confidence <= CALIBRATION_80:
                buckets["71-80"].append(evaluation)

            elif confidence <= CALIBRATION_90:
                buckets["81-90"].append(evaluation)

            else:
                buckets["91-100"].append(evaluation)


        results = {}


        for bucket, items in buckets.items():

            if not items:

                results[bucket] = {
                    "predictions": 0,
                    "accuracy": 0
                }

                continue


            correct = sum(
                1
                for item in items
                if item.correct
            )


            results[bucket] = {

                "predictions": len(items),

                "accuracy": round(
                    correct /
                    len(items)
                    *
                    MAX_SCORE,
                    2
                )

            }


        return results


    def calibration_error(
        self,
        calibration_data
    ):

        errors = []


        for bucket, data in calibration_data.items():

            if data["predictions"] == 0:
                continue


            expected = int(
                bucket.split("-")[0]
            )


            actual = data["accuracy"]


            errors.append(
                abs(
                    expected -
                    actual
                )
            )


        if not errors:

            return 0


        return round(
            sum(errors)
            /
            len(errors),
            2
        )
