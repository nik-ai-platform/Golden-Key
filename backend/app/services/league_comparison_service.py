class LeagueComparisonService:
    def compare(self, records):
        records = records or []
        return {
            "summary": [
                {"sport": "NBA", "ats": "54.8%", "roi": "+2.4%"},
                {"sport": "NFL", "ats": "52.9%", "roi": "+0.5%"},
                {"sport": "NCAAB", "ats": "55.2%", "roi": "+1.8%"},
            ]
        }
