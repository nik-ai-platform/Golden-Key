import random
import statistics


class SimulationEngine:

    DEFAULT_RUNS = 10000

    def simulate(
        self,
        npi_score: float,
        spread: float,
        runs: int = DEFAULT_RUNS
    ):

        outcomes = []

        advantage = (
            npi_score - 100
        ) / 10

        for _ in range(runs):

            random_variance = random.gauss(
                0,
                12
            )

            simulated_margin = (
                advantage
                +
                random_variance
                -
                spread
            )

            outcomes.append(
                simulated_margin
            )

        wins = sum(
            1
            for outcome in outcomes
            if outcome > 0
        )

        probability = (
            wins / runs
        ) * 100

        return {

            "runs": runs,

            "win_probability":
            round(
                probability,
                2
            ),

            "average_margin":
            round(
                statistics.mean(
                    outcomes
                ),
                2
            ),

            "standard_deviation":
            round(
                statistics.stdev(
                    outcomes
                ),
                2
            )
        }
