from app.services.prediction_engine import PredictionEngine


def test_confidence_is_bounded_to_valid_percentage_range():
    engine = PredictionEngine()

    assert engine.calculate_confidence(87.75, -22.0, {"win_probability": 28.04}) == 69.96
    assert engine.calculate_confidence(87.75, -12.74, {"win_probability": 62.74}) == engine.calculate_confidence(87.75, 12.74, {"win_probability": 62.74})
    assert engine.calculate_confidence(87.75, 12.74, {"win_probability": 62.74}) == 61.85
    assert engine.calculate_confidence(200, 100, {"win_probability": 100}) == 95