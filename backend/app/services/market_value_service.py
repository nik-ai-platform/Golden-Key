class MarketValueService:
    def calculate_value(self, model_projection, market_price):
        if model_projection is None or market_price is None:
            return {"value": "Unknown", "difference": 0}

        projection = float(model_projection)
        market = float(market_price)
        difference = round(projection - market, 2)
        if difference >= 1.5:
            label = "Strong Value"
        elif difference >= 0.5:
            label = "Value"
        else:
            label = "Fair"
        return {"value": label, "difference": difference}
