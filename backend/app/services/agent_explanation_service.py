from __future__ import annotations


class AgentExplanationService:
    def explain(self, decision: dict | None = None) -> dict:
        decision = decision or {}
        return {
            "recommended": decision.get("recommended", "PASS"),
            "reason": decision.get(
                "reason",
                "Simulation found value. Risk Agent detected volatility. Consensus confidence insufficient.",
            ),
            "why_agree": "Model alignment on historical edge.",
            "why_disagree": "Risk uncertainty offset simulation edge.",
            "factors": ["Simulation variance", "Public ownership", "Line efficiency"],
        }
