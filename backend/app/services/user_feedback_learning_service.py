from __future__ import annotations

from typing import Any


class UserFeedbackLearningService:
    def learn(self, feedback: dict[str, Any]) -> dict[str, Any]:
        return {
            "liked_prediction": feedback.get("liked_prediction"),
            "ignored_prediction": feedback.get("ignored_prediction"),
            "followed_recommendation": feedback.get("followed_recommendation"),
            "outcome": feedback.get("outcome"),
            "reason": feedback.get("reason"),
            "updated_strategy": "favor underdog value and low-volatility markets",
        }
