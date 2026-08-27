from __future__ import annotations


class AdaptiveNPIOptimizerService:
    def optimize(self, current_npi: dict | None) -> dict:
        current_npi = current_npi or {}
        proposal = current_npi.get("proposal", "Increase travel penalty: +2 points")
        return {
            "current_npi": current_npi,
            "proposal": proposal,
            "historical_improvement": "+1.4% ROI",
            "confidence": "Medium",
            "decision": "Approve",
        }
