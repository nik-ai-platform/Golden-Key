from app.services.simulation_engine import (
    SimulationEngine
)


def test_simulation_applies_signed_spread(monkeypatch):

    engine = SimulationEngine()
    monkeypatch.setattr("random.gauss", lambda _mean, _deviation: 0)

    result = engine.simulate(
        npi_score=100,
        spread=-3.5,
        runs=2
    )

    assert result["win_probability"] == 0
    assert result["average_margin"] == -3.5
    assert result["runs"] == 2
