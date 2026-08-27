import app.services.prediction_lifecycle_service as prediction_lifecycle_service


PredictionLifecycleService = (
    prediction_lifecycle_service.PredictionLifecycleService
)


def test_service_creation():
    fake_prediction_service = object()
    fake_snapshot_service = object()
    fake_version_service = object()

    service = PredictionLifecycleService(
        prediction_service=fake_prediction_service,
        snapshot_service=fake_snapshot_service,
        version_service=fake_version_service,
    )

    assert service.prediction_service is fake_prediction_service
    assert service.snapshot_service is fake_snapshot_service
    assert service.version_service is fake_version_service


def test_process_game_delegates_to_prediction_service(monkeypatch):
    expected_prediction = {"game_id": 42, "recommendation": "Home Team"}

    class _FakePredictionService:
        def __init__(self):
            self.calls = []

        def generate_prediction(self, db, game_id):
            self.calls.append((db, game_id))
            return expected_prediction

    service = PredictionLifecycleService()
    fake_prediction_service = _FakePredictionService()
    service.prediction_service = fake_prediction_service

    fake_db = object()
    result = service.process_game(fake_db, 42)

    assert fake_prediction_service.calls == [(fake_db, 42)]
    assert result == expected_prediction
