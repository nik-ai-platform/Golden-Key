class ParlayCompatibilityService:

    def calculate_compatibility_score(self, bet_a, bet_b):
        if not bet_a or not bet_b:
            return {
                "correlation_score": 0,
                "recommendation": "AVOID",
            }

        same_game = bet_a.get("game_id") == bet_b.get("game_id")
        same_selection = bet_a.get("selection") == bet_b.get("selection")
        opposing_outcomes = self._has_opposing_signs(
            bet_a.get("selection", ""),
            bet_b.get("selection", ""),
        )

        if same_game and (same_selection or opposing_outcomes):
            return {
                "correlation_score": 15,
                "recommendation": "AVOID",
            }

        return {
            "correlation_score": 80,
            "recommendation": "COMPATIBLE",
        }

    def _has_opposing_signs(self, selection_a, selection_b):
        signs = [
            self._extract_sign(selection_a),
            self._extract_sign(selection_b),
        ]
        return any(sign is not None for sign in signs) and len(set(signs)) > 1

    def _extract_sign(self, selection):
        if selection is None:
            return None

        selection_text = str(selection)
        if "+" in selection_text:
            return "PLUS"
        if "-" in selection_text:
            return "MINUS"
        return None
