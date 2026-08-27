class RiskService:

    def calculate_risk(self, factors):
        uncertainty = str(factors.get("uncertainty", "LOW")).upper()
        market_agreement = str(factors.get("market_agreement", "WEAK")).upper()
        sample_size = str(factors.get("sample_size", "MEDIUM")).upper()
        injury_uncertainty = bool(factors.get("injury_uncertainty", False))

        risk_score = 20

        if uncertainty == "HIGH":
            risk_score += 30
        elif uncertainty == "MEDIUM":
            risk_score += 15

        if market_agreement == "STRONG":
            risk_score -= 15
        elif market_agreement == "MODERATE":
            risk_score -= 5

        if sample_size == "LOW":
            risk_score += 20
        elif sample_size == "MEDIUM":
            risk_score += 10

        if injury_uncertainty:
            risk_score += 17

        risk_score = max(0, min(100, risk_score))
        if risk_score >= 70:
            risk_level = "HIGH"
        elif risk_score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
        }
