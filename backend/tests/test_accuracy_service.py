from app.services.accuracy_service import AccuracyService


def test_correct_prediction():

    service = AccuracyService()

    result = service.evaluate_prediction(
        "Team A",
        "Team A",
        85
    )

    assert result["correct"] is True
    assert result["accuracy"] == 100

def test_wrong_prediction():

    service = AccuracyService()

    result = service.evaluate_prediction(
        "Team A",
        "Team B",
        85
    )

    assert result["correct"] is False
    assert result["accuracy"] == 0
