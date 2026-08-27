from __future__ import annotations


class DecisionAgentService:
    def __init__(self) -> None:
        self.policy_strength = 1.0

    def evaluate_options(self, state: dict) -> list[dict]:
        confidence = str(state.get("confidence", "Medium"))
        options = [
            {"action": "Recommend Bet", "score": 0.7 if confidence == "High" else 0.45},
            {"action": "Avoid", "score": 0.35 if confidence == "Low" else 0.2},
            {"action": "Reduce Confidence", "score": 0.55 if confidence == "Low" else 0.25},
            {"action": "Increase Confidence", "score": 0.6 if confidence == "High" else 0.2},
            {"action": "Request More Research", "score": 0.5 if confidence == "Medium" else 0.3},
        ]
        return sorted(options, key=lambda item: item["score"], reverse=True)

    def choose_action(self, options: list[dict]) -> dict:
        if not options:
            return {"action": "Avoid", "reason": "No options provided"}
        best = max(options, key=lambda item: item.get("score", 0))
        return {"action": best["action"], "score": best["score"]}

    def update_policy(self, reward: float) -> dict:
        self.policy_strength = round(self.policy_strength + (float(reward) * 0.05), 3)
        return {
            "policy_strength": self.policy_strength,
            "status": "updated" if reward != 0 else "unchanged",
        }
