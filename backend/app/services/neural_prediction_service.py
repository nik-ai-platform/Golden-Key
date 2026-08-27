from __future__ import annotations

from typing import Any

from app.services.ml_feature_service import MLFeatureService


class NeuralPredictionService:
    """Model-agnostic prediction interface for future ML backends."""

    def predict(self, feature_vector: list[dict[str, Any]] | None) -> dict[str, Any]:
        if not feature_vector:
            return {"prediction": 0.0, "confidence": 0.0, "backend": "fallback"}

        score = sum(float(item.get("feature_value", 0.0)) for item in feature_vector) / max(1, len(feature_vector))
        return {
            "prediction": round(score, 2),
            "confidence": round(min(100.0, max(0.0, score * 10.0)), 2),
            "backend": "model-agnostic",
        }

    def predict_probability(self, game: dict[str, Any] | None) -> dict[str, Any]:
        service = MLFeatureService()
        features = service.build_features(game)
        prediction = self.predict(features)
        return {
            "game_id": game.get("game_id") if game else None,
            "probability": round(prediction["confidence"] / 100.0, 4),
            "confidence": prediction["confidence"],
            "backend": prediction["backend"],
        }
