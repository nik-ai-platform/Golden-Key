class MarketConflictDetector:

    def detect_conflict(self, model_line, market_line):
        if model_line is None or market_line is None:
            return {
                "conflict_level": "LOW_CONFLICT",
                "reason": "missing_data",
            }

        delta = abs(int(model_line) - int(market_line))
        if delta >= 6:
            return {
                "conflict_level": "HIGH_CONFLICT",
                "reason": "large_discrepancy",
            }
        if delta >= 3:
            return {
                "conflict_level": "MEDIUM_CONFLICT",
                "reason": "moderate_discrepancy",
            }
        return {
            "conflict_level": "LOW_CONFLICT",
            "reason": "aligned",
        }
