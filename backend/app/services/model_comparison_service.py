from __future__ import annotations

from app.services.analytics.backtest_service import BacktestService


class ModelComparisonService:
    """Compatibility wrapper for model comparison methods."""

    def __init__(self, backtest_service=None):
        self.backtest = backtest_service or BacktestService()

    def rank_models(self, models):
        return self.backtest.rank_models(models)

    def best_model(self, models):
        return self.backtest.best_model(models)

    def compare(self, baseline, candidate):
        if not baseline or not candidate:
            return {"recommendation": "REVIEW", "reason": "Missing model data"}

        roi_improvement = float(candidate.get("roi", 0) or 0) - float(baseline.get("roi", 0) or 0)
        ats_improvement = float(candidate.get("ats", 0) or 0) - float(baseline.get("ats", 0) or 0)
        calibration_worse = float(candidate.get("calibration", 0) or 0) < float(baseline.get("calibration", 0) or 0)

        return {
            "roi_improvement": round(roi_improvement, 2),
            "ats_improvement": round(ats_improvement, 2),
            "calibration_worse": calibration_worse,
            "recommendation": "PROMOTE" if roi_improvement > 1 and not calibration_worse else "REVIEW",
        }

    def compare_champion(self, production: dict[str, float], candidate: dict[str, float]) -> dict[str, str | float]:
        roi_improvement = float(candidate.get("roi", 0) or 0) - float(production.get("roi", 0) or 0)
        ats_improvement = float(candidate.get("ats", 0) or 0) - float(production.get("ats", 0) or 0)
        calibration_improvement = float(candidate.get("calibration", 0) or 0) - float(production.get("calibration", 0) or 0)
        decision = "Candidate Wins" if roi_improvement > 0 or ats_improvement > 0 or calibration_improvement > 0 else "Production Wins"
        return {
            "decision": decision,
            "roi_improvement": round(roi_improvement, 2),
            "ats_improvement": round(ats_improvement, 2),
            "calibration_improvement": round(calibration_improvement, 2),
        }
