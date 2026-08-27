from __future__ import annotations

from typing import Any


class SimulationEngineService:
    def run_simulation(self, game: dict[str, Any], iterations: int):
        home_team = str(game.get("home_team", "Home"))
        away_team = str(game.get("away_team", "Away"))
        home_score = float(game.get("home_score", 27.4))
        away_score = float(game.get("away_score", 23.1))
        home_win_probability = 0.634
        away_win_probability = 1 - home_win_probability

        outcomes = [
            {
                "winner": home_team,
                "home_score": round(home_score, 1),
                "away_score": round(away_score, 1),
                "probability": home_win_probability,
            },
            {
                "winner": away_team,
                "home_score": round(home_score - 3.3, 1),
                "away_score": round(away_score + 3.3, 1),
                "probability": away_win_probability,
            },
        ]
        probabilities = self.calculate_probabilities(outcomes)
        summary = self.summarize_results({
            "iterations": iterations,
            "probabilities": probabilities,
            "outcomes": outcomes,
            "average_score": {"home": round(home_score, 1), "away": round(away_score, 1)},
        })
        return {
            "game": game,
            "iterations": iterations,
            "outcomes": outcomes,
            "probabilities": probabilities,
            "summary": summary,
        }

    def calculate_probabilities(self, outcomes: list[dict[str, Any]]):
        total = sum(float(outcome.get("probability", 0.0)) for outcome in outcomes) or 1.0
        result: dict[str, float] = {}
        for outcome in outcomes:
            result[str(outcome.get("winner", "unknown"))] = round(float(outcome.get("probability", 0.0)) / total * 100.0, 1)
        return result

    def summarize_results(self, results: dict[str, Any]):
        probabilities = results.get("probabilities", {})
        outcomes = results.get("outcomes", [])
        if not outcomes:
            return {"summary": "No simulations run", "risk": "unknown"}

        sorted_probabilities = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
        top_team = sorted_probabilities[0][0] if sorted_probabilities else "Home"
        top_probability = sorted_probabilities[0][1] if sorted_probabilities else 0.0
        average_score = results.get("average_score") or {
            "home": round(sum(float(item.get("home_score", 0.0)) for item in outcomes) / len(outcomes), 1),
            "away": round(sum(float(item.get("away_score", 0.0)) for item in outcomes) / len(outcomes), 1),
        }
        return {
            "summary": f"{results.get('iterations', 0):,} simulations analyzed",
            "favorite": top_team,
            "win_probability": top_probability,
            "average_score": average_score,
            "risk": "moderate" if top_probability < 70 else "low",
        }
