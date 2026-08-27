class MarketMovementService:
    def detect_movement(self, opening, current):
        if opening is None or current is None:
            return {"direction": "stable", "magnitude": 0.0, "signal": "No movement"}

        delta = float(current) - float(opening)
        if delta >= 3:
            signal = "Strong Money Movement"
        elif delta >= 1:
            signal = "Moderate Movement"
        else:
            signal = "Stable"
        return {"direction": "up" if delta > 0 else "down", "magnitude": round(abs(delta), 2), "signal": signal}
