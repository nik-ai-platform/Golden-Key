class ModelPerformanceService:

    def summarize(self, metrics):
        if not metrics:
            return {
                "overall_accuracy": 0.0,
                "ats": 0.0,
                "roi": 0.0,
                "confidence_calibration": 0.0,
                "sport_performance": {},
                "market_type_performance": {},
            }

        return {
            "overall_accuracy": metrics.get("overall_accuracy", 0.0),
            "ats": metrics.get("ats", 0.0),
            "roi": metrics.get("roi", 0.0),
            "confidence_calibration": metrics.get("confidence_calibration", 0.0),
            "sport_performance": metrics.get("sport_performance", {}),
            "market_type_performance": metrics.get("market_type_performance", {}),
        }
