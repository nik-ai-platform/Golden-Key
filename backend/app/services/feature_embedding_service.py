from __future__ import annotations

from typing import Any


class FeatureEmbeddingService:
    """Normalizes and encodes categorical and contextual sports features into vectors."""

    def encode(self, game: dict[str, Any] | None) -> list[float]:
        if not game:
            return []

        return [
            float(game.get("rest_days", 0) or 0),
            float(self._encode_token(game.get("home_team"))),
            float(self._encode_token(game.get("away_team"))),
            float(self._encode_token(game.get("weather"))),
            float(self._encode_token(game.get("market"))),
            float(self._encode_token(game.get("injury"))),
            float(game.get("travel", 0) or 0),
            float(self._encode_token(game.get("schedule"))),
            float(self._encode_token(game.get("coach"))),
        ]

    @staticmethod
    def _encode_token(value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            return sum(ord(ch) for ch in value) % 100
        return 0
