class SportIntelligenceService:
    def get_model(self, sport):
        sport = (sport or "NBA").upper()
        registry = {
            "NBA": "NPI-NBA-v5.4",
            "NFL": "NPI-NFL-v4.8",
            "NCAAB": "NPI-NCAAB-v3.2",
            "WNBA": "NPI-WNBA-v2.1",
        }
        return {"sport": sport, "model": registry.get(sport, "NPI-DEFAULT-v1"), "health": "Excellent" if sport in {"NBA", "NFL"} else "Testing"}

    def get_features(self, sport):
        sport = (sport or "NBA").upper()
        features = {
            "NBA": ["pace", "efficiency", "rest"],
            "NFL": ["matchup", "weather", "injury"],
            "NCAAB": ["tempo", "shot_profile", "rest"],
            "WNBA": ["pace", "usage", "rest"],
        }
        return {"sport": sport, "features": features.get(sport, ["pace"]) }

    def compare_sports(self, sports):
        sports = sports or []
        return [self.get_model(sport) for sport in sports]
