from app.services.model_evaluation_service import ModelEvaluationService


def _games():
    return [
        {
            "actual_winner": "HOME",
            "predictions": {
                "NPI-v3": {"winner": "HOME", "confidence": 82.0},
                "NPI-v4": {"winner": "HOME", "confidence": 79.0},
            },
        },
        {
            "actual_winner": "AWAY",
            "predictions": {
                "NPI-v3": {"winner": "HOME", "confidence": 77.0},
                "NPI-v4": {"winner": "AWAY", "confidence": 75.0},
            },
        },
        {
            "actual_winner": "HOME",
            "predictions": {
                "NPI-v3": {"winner": "HOME", "confidence": 80.0},
                "NPI-v4": {"winner": "HOME", "confidence": 76.0},
            },
        },
    ]


def test_same_input_produces_repeatable_evaluation_results():
    service = ModelEvaluationService(min_sample_size=2)
    games = _games()

    first = service.evaluate_model("NPI-v3", games)
    second = service.evaluate_model("NPI-v3", games)

    assert first.model_dump() == second.model_dump()


def test_candidate_and_current_are_evaluated_on_identical_dataset():
    service = ModelEvaluationService(min_sample_size=2)
    games = _games()

    current = service.evaluate_model("NPI-v3", games)
    candidate = service.evaluate_model("NPI-v4", games)

    assert current.predictions == len(games)
    assert candidate.predictions == len(games)


def test_promotion_recommendation_honors_minimum_sample_size_rule():
    service = ModelEvaluationService(min_sample_size=4)
    comparison = service.compare_models(
        {
            "accuracy": 70.0,
            "calibration": 12.0,
            "average_confidence": 75.0,
            "predictions": 10,
        },
        {
            "accuracy": 74.0,
            "calibration": 10.0,
            "average_confidence": 76.0,
            "predictions": 3,
        },
    )

    assert comparison.winner == "current"


def test_missing_historical_data_is_handled_gracefully():
    service = ModelEvaluationService()

    metric = service.evaluate_model("NPI-v4", games=[])

    assert metric.accuracy == 0.0
    assert metric.calibration == 0.0
    assert metric.average_confidence == 0.0
    assert metric.predictions == 0


def test_comparison_metrics_are_calculated_correctly():
    service = ModelEvaluationService(min_sample_size=2)
    games = _games()

    current = service.evaluate_model("NPI-v3", games)
    candidate = service.evaluate_model("NPI-v4", games)
    comparison = service.compare_models(current, candidate)

    assert current.accuracy == 66.67
    assert candidate.accuracy == 100.0
    assert current.average_confidence == 79.67
    assert candidate.average_confidence == 76.67
    assert comparison.winner == "candidate"