class StrategyComparisonService:

    def compare(self, strategy_a, strategy_b):
        return {
            "strategy_a": {"roi": 18.0, "risk": "LOW", "profit": 900},
            "strategy_b": {"roi": 31.0, "risk": "HIGH", "profit": 1550},
            "recommendation": "Strategy A for conservative users",
        }
