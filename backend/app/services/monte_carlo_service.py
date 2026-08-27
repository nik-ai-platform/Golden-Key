import random


class MonteCarloService:

    def run(self, simulations):
        count = int(simulations or 0)
        outcomes = [random.uniform(-2100, 4800) for _ in range(count)]
        average = sum(outcomes) / len(outcomes) if outcomes else 0
        return {
            "simulations": count,
            "expected_outcome": round(average, 2),
            "best_case": round(max(outcomes), 2) if outcomes else 0,
            "worst_case": round(min(outcomes), 2) if outcomes else 0,
        }
