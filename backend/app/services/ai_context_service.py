from __future__ import annotations

from typing import Any


class AIContextService:
    def build_context(self, user: Any, message: str) -> dict[str, Any]:
        profile = getattr(user, "profile", None) if user else None
        if profile is None:
            profile = {
                "risk_level": "Moderate",
                "bankroll": 5000,
                "favorite_team": "Atlanta Hawks",
                "favorite_sports": ["NBA", "NCAAB"],
                "betting_style": "underdog value",
            }

        return {
            "user_profile": profile,
            "favorite_teams": profile.get("favorite_teams", [profile.get("favorite_team", "Atlanta Hawks")]),
            "risk_profile": profile.get("risk_level", "Moderate"),
            "current_bets": profile.get("current_bets", [{"market": "ATS", "position": "Boston -4.5"}]),
            "recent_predictions": profile.get("recent_predictions", [{"sport": "NBA", "result": "Win"}]),
            "live_games": profile.get("live_games", [{"game": "Lakers vs Rockets", "status": "Live"}]),
            "bankroll": profile.get("bankroll", 5000),
            "confidence": 82,
            "message": message,
        }
