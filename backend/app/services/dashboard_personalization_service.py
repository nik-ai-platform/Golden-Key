from __future__ import annotations

from typing import Any


class DashboardPersonalizationService:
    def build_dashboard(self, user_profile: dict[str, Any]) -> dict[str, Any]:
        sports = user_profile.get("preferred_sports", ["NBA"])
        if "NFL" in sports:
            return {
                "favorite_sports": sports,
                "preferred_metrics": ["spread models", "weather", "qb analysis"],
                "layout": "futures-first",
                "alert_settings": ["line movement", "weather alerts"],
            }

        return {
            "favorite_sports": sports,
            "preferred_metrics": ["player impact", "rest", "line movement"],
            "layout": "game-flow",
            "alert_settings": ["injury alerts", "late line movement"],
        }
