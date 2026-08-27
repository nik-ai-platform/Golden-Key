class DailyReportService:

    def generate_report(self, opportunities=None):
        if not opportunities:
            opportunities = [
                {"name": "NBA BOS -3.5", "value_score": 88},
                {"name": "NFL KC ML", "value_score": 84},
            ]

        return {
            "title": "Golden Key Daily Report",
            "top_opportunities": opportunities,
            "avoid": [{"name": "NYK -8", "reason": "Market agrees with model."}],
        }
