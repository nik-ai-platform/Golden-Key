class CLVService:
    def calculate_clv(self, bet_line, closing_line):
        if bet_line is None or closing_line is None:
            return 0.0
        return round(float(closing_line) - float(bet_line), 2)

    def summarize(self, records):
        records = records or []
        if not records:
            return {"average_clv": 0.0, "count": 0}
        clv_values = [float(item.get("clv", 0.0) or 0.0) for item in records]
        return {
            "average_clv": round(sum(clv_values) / len(clv_values), 2),
            "count": len(clv_values),
        }
