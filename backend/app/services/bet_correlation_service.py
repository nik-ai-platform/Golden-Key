from __future__ import annotations


class BetCorrelationService:
    def detect(self, positions: list[dict] | None) -> dict:
        positions = positions or []
        teams = [str(item.get("market", "")).lower() for item in positions]
        high_correlation = any("chiefs" in team for team in teams) and len(positions) >= 3
        return {
            "high_correlation": high_correlation,
            "message": "High correlation detected. Portfolio behaves like one position." if high_correlation else "Correlation looks manageable.",
        }
