class LiveOddsService:

    def track_movement(self, opening_line, current_line):
        if opening_line is None or current_line is None:
            return {
                "opening_line": None,
                "current_line": None,
                "live_line": None,
                "movement_speed": 0,
                "direction": "FLAT",
                "movement": 0,
            }

        opening_value = float(opening_line)
        current_value = float(current_line)
        movement = round(current_value - opening_value, 2)
        direction = "UP" if movement > 0 else "DOWN" if movement < 0 else "FLAT"
        return {
            "opening_line": opening_value,
            "current_line": current_value,
            "live_line": current_value,
            "movement_speed": abs(movement),
            "direction": direction,
            "movement": movement,
        }
