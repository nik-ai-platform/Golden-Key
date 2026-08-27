from __future__ import annotations

from typing import Any


class MLFeatureService:
    """Builds, validates, and exports ML features in a model-agnostic form."""

    def build_features(self, game: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not game:
            return []

        feature_specs = [
            ("rest_days", game.get("rest_days", 0)),
            ("weather", game.get("weather", "clear")),
            ("market", game.get("market", "spread")),
            ("injury", game.get("injury", "none")),
            ("travel", game.get("travel", 0)),
            ("schedule", game.get("schedule", "regular")),
            ("coach", game.get("coach", "neutral")),
        ]

        features = []
        for name, value in feature_specs:
            features.append(
                {
                    "feature_name": name,
                    "feature_value": self._normalize_value(value),
                    "feature_version": "2.2",
                    "game_id": game.get("game_id"),
                    "sport": game.get("sport"),
                }
            )

        return features

    def validate_features(self, features: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        if not features:
            return []

        return [
            {
                **feature,
                "feature_value": self._normalize_value(feature.get("feature_value")),
            }
            for feature in features
            if feature.get("feature_name")
        ]

    def export_training_dataset(self, sport: str | None) -> list[dict[str, Any]]:
        return [
            {
                "sport": sport or "NBA",
                "features": [
                    {"feature_name": "rest_days", "feature_value": 3, "feature_version": "2.2"},
                    {"feature_name": "travel", "feature_value": 1, "feature_version": "2.2"},
                ],
            }
        ]

    @staticmethod
    def _normalize_value(value: Any) -> float:
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(len(value))
        return 0.0
