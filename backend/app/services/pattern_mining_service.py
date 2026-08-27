from __future__ import annotations

from typing import Any


class PatternMiningService:
    def mine_patterns(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "condition": "Home team + spread -3 to -6 + opponent on 3rd road game",
                "historical_ats": 57.8,
                "signal": "Repeated outcome",
            },
            {
                "condition": "Away team with rest disadvantage greater than 2 days",
                "historical_ats": 54.1,
                "signal": "Situational trend",
            },
            {
                "condition": "Closing line move against public sentiment",
                "historical_ats": 55.6,
                "signal": "Hidden correlation",
            },
            {
                "condition": "Weather + travel + injury stack",
                "historical_ats": 56.2,
                "signal": "Conditional pattern",
            },
        ]
