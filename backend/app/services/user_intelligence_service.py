from __future__ import annotations

from typing import Any

from app.models.user_intelligence_profile import UserIntelligenceProfile
from app.models.user_behavior import UserBehavior


class UserIntelligenceService:
    def __init__(self) -> None:
        self._profiles: dict[int, UserIntelligenceProfile] = {}
        self._behaviors: dict[int, UserBehavior] = {}

    def build_profile(self, user_id: int) -> dict[str, Any]:
        profile = self._profiles.get(user_id)
        if profile is None:
            profile = UserIntelligenceProfile(user_id=user_id, risk_level="moderate", preferred_sports=["NBA", "NFL"], preferred_bet_types=["ATS"], average_stake=100, favorite_markets=["ATS"], confidence_threshold=78)
            profile.id = user_id
            self._profiles[user_id] = profile

        return {
            "user_id": profile.user_id,
            "risk_level": profile.risk_level,
            "preferred_sports": profile.preferred_sports or ["NBA"],
            "preferred_bet_types": profile.preferred_bet_types or ["ATS"],
            "average_stake": profile.average_stake,
            "favorite_markets": profile.favorite_markets or ["ATS"],
            "confidence_threshold": profile.confidence_threshold,
        }

    def update_preferences(self, behavior: dict[str, Any]) -> dict[str, Any]:
        user_id = behavior.get("user_id", 1)
        behavior_model = UserBehavior(
            id=f"behavior{user_id}",
            user_id=user_id,
            games_viewed=behavior.get("games_viewed", 0),
            predictions_viewed=behavior.get("predictions_viewed", 0),
            bets_accepted=behavior.get("bets_accepted", 0),
            bets_ignored=behavior.get("bets_ignored", 0),
            favorite_teams=behavior.get("favorite_teams", ["Hawks"]),
            average_odds=behavior.get("average_odds", "-110"),
            win_loss_patterns=behavior.get("win_loss_patterns", {"win": 3, "loss": 1}),
            bankroll_changes=behavior.get("bankroll_changes", {"current": 5000}),
        )
        self._behaviors[user_id] = behavior_model
        return {
            "user_id": user_id,
            "updated": True,
            "behavior": {
                "games_viewed": behavior_model.games_viewed,
                "predictions_viewed": behavior_model.predictions_viewed,
                "bets_accepted": behavior_model.bets_accepted,
                "bets_ignored": behavior_model.bets_ignored,
                "favorite_teams": behavior_model.favorite_teams,
            },
        }

    def calculate_user_fit(self, prediction: dict[str, Any]) -> dict[str, Any]:
        profile = self.build_profile(prediction.get("user_id", 1))
        confidence = float(prediction.get("confidence", 0) or 0)
        threshold = float(profile["confidence_threshold"] or 0)
        fit_score = min(100.0, max(0.0, confidence + (10 if profile["risk_level"] == "moderate" else 0) - max(0, threshold - confidence) * 0.3))
        return {
            "prediction": prediction.get("title", "Prediction"),
            "fit_score": round(fit_score, 1),
            "match": fit_score >= 80,
        }
