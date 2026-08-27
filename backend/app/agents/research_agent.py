from __future__ import annotations


class ResearchAgent:
    name = "research_agent"

    def analyze(self, game: dict) -> dict:
        return {
            "relevant_trend": "Home favorites after rest: 56.7%",
            "signals": ["Historical Trends", "Situational Angles", "Pattern Matches"],
            "game": game,
        }
