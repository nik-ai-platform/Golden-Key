from app.services.simulation_engine import (
    SimulationEngine
)


def test_simulation_returns_probability():

    engine = SimulationEngine()

    result = engine.simulate(
        npi_score=150,
        spread=-3.5,
        runs=1000
    )

    assert (
        0 <= result["win_probability"] <= 100
    )

    assert (
        result["runs"] == 1000
    )
