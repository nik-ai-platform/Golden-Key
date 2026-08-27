from __future__ import annotations

from typing import Any

from app.services.user_intelligence_service import UserIntelligenceService


class PersonalizedPredictionService:
    def __init__(self) -> None:
        self.user_intelligence_service = UserIntelligenceService()

    def personalize(self, prediction: dict[str, Any], user_id: int) -> dict[str, Any]:
        profile = self.user_intelligence_service.build_profile(user_id)
        fit = self.user_intelligence_service.calculate_user_fit({**prediction, "user_id": user_id})

        if profile["preferred_bet_types"] and "ATS" in profile["preferred_bet_types"]:
            fit_score = fit["fit_score"] + 6
        else:
            fit_score = fit["fit_score"] - 3

        return {
            "prediction": prediction.get("title", "Prediction"),
            "recommended_action": "MATCH" if fit_score >= 90 else "LOWER FIT",
            "fit_score": round(fit_score, 1),
            "profile": profile,
        }
