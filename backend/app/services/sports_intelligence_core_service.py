from __future__ import annotations

from typing import Any


class SportsIntelligenceCoreService:
    def analyze(self, question: str) -> dict[str, Any]:
        market_perception = "negative" if "undervalued" in question.lower() else "neutral"
        metrics = "strong"
        simulation = "positive"

        combined = self.combine_models(
            {
                "market_perception": market_perception,
                "underlying_metrics": metrics,
                "simulation": simulation,
                "question": question,
            }
        )
        reasoning = self.generate_reasoning(combined)

        return {
            "question": question,
            "market_perception": market_perception,
            "underlying_metrics": metrics,
            "simulation": simulation,
            "conclusion": combined["conclusion"],
            "reasoning": reasoning,
        }

    def combine_models(self, inputs: dict[str, Any]) -> dict[str, Any]:
        market = str(inputs.get("market_perception", "neutral"))
        metrics = str(inputs.get("underlying_metrics", "mixed"))
        simulation = str(inputs.get("simulation", "neutral"))

        if market == "negative" and metrics == "strong" and simulation == "positive":
            conclusion = "Potential value opportunity"
            score = 0.78
        elif metrics == "strong" and simulation == "positive":
            conclusion = "Constructive signal with moderate value"
            score = 0.66
        else:
            conclusion = "No clear edge"
            score = 0.44

        return {
            **inputs,
            "conclusion": conclusion,
            "confidence": score,
        }

    def generate_reasoning(self, results: dict[str, Any]) -> str:
        return (
            "Market perception is {market}; underlying metrics are {metrics}; "
            "simulation is {simulation}. Conclusion: {conclusion}."
        ).format(
            market=results.get("market_perception", "neutral"),
            metrics=results.get("underlying_metrics", "mixed"),
            simulation=results.get("simulation", "neutral"),
            conclusion=results.get("conclusion", "No clear edge"),
        )
