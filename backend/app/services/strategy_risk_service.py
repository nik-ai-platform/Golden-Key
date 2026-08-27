class StrategyRiskService:

    def score(self, metrics):
        volatility = (metrics or {}).get("volatility", "medium")
        variance = float((metrics or {}).get("variance", 0.0) or 0.0)
        downside_risk = float((metrics or {}).get("downside_risk", 0.0) or 0.0)
        losing_streak_probability = float((metrics or {}).get("losing_streak_probability", 0.0) or 0.0)
        sample_size = int((metrics or {}).get("sample_size", 0) or 0)

        if volatility == "low" and variance < 0.1 and downside_risk < 0.15 and sample_size >= 50:
            risk = "LOW"
            score = 82
        elif volatility == "high" or losing_streak_probability > 0.3:
            risk = "HIGH"
            score = 58
        else:
            risk = "MEDIUM"
            score = 69

        return {
            "score": score,
            "risk": risk,
            "expected_drawdown": round(max(downside_risk * 100, 8), 2),
        }
