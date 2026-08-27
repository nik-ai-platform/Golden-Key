from __future__ import annotations


class PolicyManagementService:
    def __init__(self) -> None:
        self._version = "v1.8"

    def snapshot(self) -> dict:
        return {
            "agent_version": self._version,
            "decision_rules": "Better injury weighting",
            "performance": "Improving",
            "changes": ["Updated injury factor", "Adjusted volatility threshold"],
            "approval_status": "Testing",
        }

    def update(self, change: str, approved: bool = False) -> dict:
        self._version = "v2.1" if approved else "v2.0"
        return {
            "agent_version": self._version,
            "changes": [change],
            "approval_status": "Approved" if approved else "Review",
        }
