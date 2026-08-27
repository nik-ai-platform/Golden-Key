from __future__ import annotations

from typing import Any


class PersonalAlertService:
    def build_alerts(self, preferences: dict[str, Any], live_opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        favorite_teams = preferences.get("favorite_teams", [])
        alerts = []
        for opportunity in live_opportunities:
            if favorite_teams and opportunity.get("team") in favorite_teams:
                alerts.append({
                    "message": f"Your preferred {preferences.get('sport', 'NBA')} value alert: {opportunity.get('team')} +{opportunity.get('spread')} matches your strategy.",
                    "priority": "high",
                })
        return alerts or [{"message": "Lakers game available", "priority": "normal"}]
