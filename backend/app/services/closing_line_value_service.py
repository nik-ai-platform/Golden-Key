from app.services.market_intelligence_service import MarketIntelligenceService


class ClosingLineValueService:

    def __init__(self, market_intelligence_service=None):
        self.market = market_intelligence_service or MarketIntelligenceService()

    def calculate_clv(self, predicted_line, closing_line, market_type="spread"):
        if predicted_line is None or closing_line is None:
            return 0.0
        if market_type == "moneyline":
            return round(
                self.market._implied_probability(float(closing_line))
                - self.market._implied_probability(float(predicted_line)),
                2,
            )
        return round(abs(float(closing_line)) - abs(float(predicted_line)), 2)
