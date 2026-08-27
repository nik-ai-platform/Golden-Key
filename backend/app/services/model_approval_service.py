from __future__ import annotations


class ModelApprovalService:
    """Requires explicit promotion rather than auto-deploying a candidate."""

    def approve(self, candidate_metrics: dict[str, float], require_manual: bool = True) -> dict[str, bool | str]:
        if require_manual:
            return {"approved": False, "status": "Pending Manual Approval"}
        return {"approved": True, "status": "Approved"}

    def promote(self, candidate_metrics: dict[str, float], manual_approval: bool = False) -> dict[str, bool | str]:
        if not manual_approval:
            return {"approved": False, "status": "Pending Manual Approval"}
        return {"approved": True, "status": "Production"}
