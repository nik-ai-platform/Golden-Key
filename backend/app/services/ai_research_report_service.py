from __future__ import annotations

from typing import Any


class AIResearchReportService:
    def generate_report(
        self,
        discovery: dict[str, Any],
        evidence: dict[str, Any],
        backtest: dict[str, Any],
        risk: dict[str, Any],
        recommendation: str,
        next_steps: list[str],
    ) -> dict[str, Any]:
        return {
            "discovery": discovery,
            "evidence": evidence,
            "backtest": backtest,
            "risk": risk,
            "recommendation": recommendation,
            "next_steps": next_steps,
        }
