class KellyService:

    def calculate_fraction(self, odds, probability):
        if odds is None or probability is None:
            return 0.0

        decimal_odds = float(odds)
        p = float(probability)
        q = 1 - p

        if decimal_odds <= 1:
            return 0.0

        b = decimal_odds - 1
        full_kelly = (b * p - q) / b

        if full_kelly <= 0:
            return 0.0

        return round(min(full_kelly * 0.25, 0.25), 4)

    def evaluate_edge(self, odds, probability):
        fraction = self.calculate_fraction(odds, probability)
        if fraction > 0:
            return {
                "edge": "Positive edge detected",
                "fraction": fraction,
            }
        return {
            "edge": "No positive edge",
            "fraction": 0.0,
        }
