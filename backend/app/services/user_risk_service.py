class UserRiskService:
    RISK_LEVELS = ["CONSERVATIVE", "MODERATE", "AGGRESSIVE", "PROFESSIONAL"]

    def get_risk_filters(self, risk_level):
        risk_level = (risk_level or "MODERATE").upper()
        if risk_level == "CONSERVATIVE":
            return {
                "minimum_confidence": 80,
                "minimum_edge": 2.5,
                "allow_parlays": False,
                "allow_high_variance": False,
                "volatility": "low",
            }
        if risk_level == "AGGRESSIVE":
            return {
                "minimum_confidence": 60,
                "minimum_edge": 1.5,
                "allow_parlays": True,
                "allow_high_variance": True,
                "volatility": "high",
            }
        if risk_level == "PROFESSIONAL":
            return {
                "minimum_confidence": 70,
                "minimum_edge": 3.0,
                "allow_parlays": True,
                "allow_high_variance": False,
                "volatility": "medium",
            }
        return {
            "minimum_confidence": 70,
            "minimum_edge": 2.0,
            "allow_parlays": False,
            "allow_high_variance": False,
            "volatility": "medium",
        }
