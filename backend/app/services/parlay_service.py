class ParlayService:

    def generate_parlays(self, available_bets, max_legs=3):
        if not available_bets:
            return []

        max_legs = max(1, min(int(max_legs or 3), 3))
        parlays = []
        for index, bet in enumerate(available_bets[:max_legs]):
            parlays.append(
                {
                    "legs": [bet.get("selection", "")],
                    "probability": self.calculate_probability([bet]),
                    "value_score": self.calculate_value([bet]),
                    "risk_score": 25 + index,
                    "stake": 0,
                }
            )
        return parlays

    def calculate_probability(self, legs):
        if not legs:
            return 0.0

        combined = 1.0
        for leg in legs:
            probability = float(leg.get("probability", 0) or 0)
            combined *= probability
        return round(combined * 100, 2)

    def calculate_value(self, legs):
        if not legs:
            return 0

        base_quality = sum(int(leg.get("quality_score", 0) or 0) for leg in legs)
        return min(100, max(0, int(round(base_quality / max(1, len(legs))))))

    def rank_parlays(self, parlays):
        if not parlays:
            return []

        return sorted(
            parlays,
            key=lambda item: (
                item.get("value_score", 0),
                -(item.get("risk_score", 0)),
            ),
            reverse=True,
        )
