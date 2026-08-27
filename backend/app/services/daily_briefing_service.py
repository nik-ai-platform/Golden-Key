from __future__ import annotations

from typing import Any


class DailyBriefingService:
    def generate_briefing(self, profile: dict[str, Any]) -> dict[str, Any]:
        sport = (profile.get("preferred_sports") or ["NBA"])[0]
        return {
            "headline": f"Good Morning {profile.get('user_name', 'Nik')}",
            "best_opportunities": [f"{sport} value spot: Celtics -4 with 84% confidence"],
            "portfolio_review": "ROI +6.4%",
            "risk": "Low",
            "alerts": ["Line movement detected"],
            "model_updates": ["Calibration improved"],
        }
