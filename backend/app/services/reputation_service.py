class ReputationService:
    def calculate_reputation(self, metrics: dict) -> dict:
        accuracy = float(metrics.get("prediction_accuracy", 0.0))
        roi = float(metrics.get("roi", 0.0))
        consistency = float(metrics.get("consistency", 0.0))
        feedback = float(metrics.get("community_feedback", 0.0))
        analysis_quality = float(metrics.get("analysis_quality", 0.0))
        longevity = float(metrics.get("longevity", 0.0))
        verified = bool(metrics.get("verified", False))

        score = round(
            (accuracy * 28)
            + (roi * 24)
            + (consistency * 20)
            + (feedback * 18)
            + (analysis_quality * 16)
            + (longevity * 14)
            + (6 if verified else 0),
            1,
        )

        if score > 100:
            score = 100.0

        return {
            "score": score,
            "verified": verified,
            "summary": "High standing" if score >= 85 else "Developing reputation",
        }
