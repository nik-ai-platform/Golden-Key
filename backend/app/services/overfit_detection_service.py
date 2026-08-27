from __future__ import annotations


class OverfitDetectionService:
    def assess(self, sample_size: int, ats_percentage: float) -> dict[str, str | int | float]:
        if sample_size < 50 and ats_percentage >= 70:
            status = "reject"
            reason = "small sample likely reflects noise"
        elif sample_size >= 1000 and ats_percentage >= 55:
            status = "accept"
            reason = "large sample supports signal quality"
        else:
            status = "review"
            reason = "needs more validation"

        return {
            "status": status,
            "reason": reason,
            "sample_size": sample_size,
            "ats_percentage": ats_percentage,
        }
