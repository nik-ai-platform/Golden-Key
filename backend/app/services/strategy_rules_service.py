class StrategyRulesService:

    def build_rules(self, payload):
        return {
            "sport": payload.get("sport"),
            "market": payload.get("market"),
            "confidence_threshold": payload.get("confidence_threshold"),
            "minimum_edge": payload.get("minimum_edge"),
            "odds_range": payload.get("odds_range"),
            "spread_range": payload.get("spread_range"),
            "parlay_rules": payload.get("parlay_rules"),
            "bankroll_rules": payload.get("bankroll_rules"),
        }
