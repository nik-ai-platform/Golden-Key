from __future__ import annotations


class FeatureEvolutionService:
    def evolve(self, current_importance: dict | None) -> dict:
        current_importance = current_importance or {}
        rest = float(current_importance.get("rest", 8) or 8)
        improved_rest = round(rest + 3, 1)
        return {
            "which_factors_improve_accuracy": ["Rest", "Defense", "Market movement"],
            "which_factors_decline": ["Injuries", "Travel"],
            "less_predictive": ["Legacy pace metrics"],
            "suggested_update": {"rest": improved_rest},
        }
