from __future__ import annotations


class PredictionFeedbackService:
    def process(self, prediction: dict | None, actual_result: dict | str | None) -> dict:
        prediction = prediction or {}
        predicted = prediction.get("prediction") or prediction.get("winner") or prediction.get("market")
        actual_text = actual_result.get("result") if isinstance(actual_result, dict) else actual_result
        error = 0.0 if str(predicted).lower() == str(actual_text).lower() else 1.0
        return {
            "prediction": predicted,
            "actual_result": actual_text,
            "error_score": error,
            "learning_signal": "Store learning signal",
        }
