from app.scheduler.job_scheduler import JobScheduler


class _Monitor:
    def __init__(self):
        self.calls = []

    def log_scheduler(self, message, **context):
        self.calls.append((message, context))


def test_scheduler_handles_missing_outcomes_and_continues_learning_steps():
    class _ImportService:
        def import_games(self, _db, _sport):
            class _Game:
                id = 9

            return [_Game()]

    class _PredictionService:
        def generate_prediction(self, _db, game_id):
            return {"game_id": game_id}

    class _OutcomeService:
        def evaluate_completed_games(self, _db):
            return []

        def update_prediction_metrics(self, _db):
            return {"winner_accuracy": 0.0, "total_outcomes": 0}

    class _DatasetService:
        def __init__(self):
            self.build_calls = 0

        def build_dataset(self, *args, **kwargs):
            self.build_calls += 1
            return []

        def validate_dataset(self, dataset):
            return {"valid": True, "records": len(dataset), "errors": []}

    class _TrainingService:
        def __init__(self):
            self.calls = 0

        def evaluate_candidate_models(self, games):
            self.calls += 1
            assert games == []
            return []

    monitor = _Monitor()
    dataset_service = _DatasetService()
    training_service = _TrainingService()

    scheduler = JobScheduler(
        import_service=_ImportService(),
        prediction_service=_PredictionService(),
        outcome_service=_OutcomeService(),
        dataset_service=dataset_service,
        training_service=training_service,
        monitor=monitor,
    )

    predictions = scheduler.run(db=object(), sport="wnba")

    assert len(predictions) == 1
    assert dataset_service.build_calls == 1
    assert training_service.calls == 1
    assert any(call[0] == "Evaluated completed games" for call in monitor.calls)