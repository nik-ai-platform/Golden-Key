from app.services.model_training_service import ModelTrainingService


class _DatasetService:
    def __init__(self, dataset):
        self.dataset = dataset

    def build_dataset(self, *_args, **_kwargs):
        return list(self.dataset)

    def validate_dataset(self, dataset):
        valid = bool(dataset)
        return {"valid": valid, "errors": [] if valid else ["empty"], "records": len(dataset)}


class _VersionService:
    def __init__(self, current="NPI-v3"):
        self.current = current

    def get_current_version(self):
        return self.current

    def set_current_version(self, version):
        self.current = version


class _Metric:
    def __init__(self, accuracy, calibration, average_confidence, predictions):
        self.accuracy = accuracy
        self.calibration = calibration
        self.average_confidence = average_confidence
        self.predictions = predictions


class _Comparison:
    def __init__(self, winner, current_model, candidate_model):
        self.winner = winner
        self.current_model = current_model
        self.candidate_model = candidate_model

    def model_dump(self):
        return {
            "winner": self.winner,
            "current_model": {
                "accuracy": self.current_model.accuracy,
                "calibration": self.current_model.calibration,
                "average_confidence": self.current_model.average_confidence,
                "predictions": self.current_model.predictions,
            },
            "candidate_model": {
                "accuracy": self.candidate_model.accuracy,
                "calibration": self.candidate_model.calibration,
                "average_confidence": self.candidate_model.average_confidence,
                "predictions": self.candidate_model.predictions,
            },
        }


class _EvaluationService:
    def evaluate_model(self, version, _games):
        if version == "NPI-v4":
            return _Metric(74.2, 1.8, 79.2, 400)
        return _Metric(72.8, 2.5, 80.0, 400)

    def compare_models(self, current, candidate):
        winner = "candidate" if candidate.accuracy > current.accuracy and candidate.calibration <= current.calibration else "current"
        return _Comparison(winner, current, candidate)


class _BacktestingService:
    def simulate_predictions(self, games, _model, model_version=None):
        return [
            {
                "predicted_winner": ((game.get("predictions") or {}).get(model_version) or {}).get("winner", "home"),
                "actual_winner": game.get("actual_winner"),
                "confidence": ((game.get("predictions") or {}).get(model_version) or {}).get("confidence", 70.0),
                "bet_outcome": "win",
            }
            for game in games
        ]

    def calculate_results(self, predictions):
        return {
            "games_tested": len(predictions),
            "correct_predictions": len(predictions),
            "accuracy": 60.0,
            "confidence_accuracy": 74.0,
            "calibration_error": 18.0,
            "ats_record": f"{len(predictions)}-0",
            "roi": 5.1,
            "max_drawdown": 0.0,
            "failed_simulations": 0,
        }

    def generate_report(self, results):
        return {
            "games": results["games_tested"],
            "accuracy": results["accuracy"],
            "roi": results["roi"],
            "calibration_error": results["calibration_error"],
            "recommendation": "promote",
        }


def _dataset():
    return [
        {
            "sport": "WNBA",
            "confidence": 84.0,
            "winner": "home",
            "correct": True,
            "model_version": "NPI-v3",
            "home_strength": 82.4,
            "away_strength": 76.8,
        }
    ]


def test_candidate_models_cannot_bypass_evaluation():
    service = ModelTrainingService(
        dataset_service=_DatasetService(_dataset()),
        evaluation_service=_EvaluationService(),
        version_service=_VersionService("NPI-v3"),
    )

    service.train_candidate(version="NPI-v4")

    try:
        service.submit_for_review("NPI-v4", admin_approved=True)
        assert False, "Expected PermissionError"
    except PermissionError:
        assert True


def test_promotion_requires_admin_approval_even_after_passed_evaluation():
    service = ModelTrainingService(
        dataset_service=_DatasetService(_dataset()),
        evaluation_service=_EvaluationService(),
        version_service=_VersionService("NPI-v3"),
    )

    service.train_candidate(version="NPI-v4")
    service.evaluate_candidate("NPI-v4", games=[{"actual_winner": "home"}])

    result = service.submit_for_review("NPI-v4", admin_approved=False)

    assert result["deployed"] is False
    assert service.version_service.get_current_version() == "NPI-v3"


def test_admin_approval_promotes_candidate_to_production():
    service = ModelTrainingService(
        dataset_service=_DatasetService(_dataset()),
        evaluation_service=_EvaluationService(),
        version_service=_VersionService("NPI-v3"),
    )

    service.train_candidate(version="NPI-v4")
    service.evaluate_candidate("NPI-v4", games=[{"actual_winner": "home"}])

    result = service.submit_for_review(
        "NPI-v4",
        admin_approved=True,
        approved_by="admin-user",
    )

    assert result["deployed"] is True
    assert service.version_service.get_current_version() == "NPI-v4"
    assert service.candidates["NPI-v4"]["status"] == ModelTrainingService.PRODUCTION


def test_learning_dashboard_summarizes_training_state():
    service = ModelTrainingService(
        dataset_service=_DatasetService(_dataset()),
        evaluation_service=_EvaluationService(),
        version_service=_VersionService("NPI-v3"),
    )

    service.train_candidate(version="NPI-v4")
    service.evaluate_candidate("NPI-v4", games=[{"actual_winner": "home"}])

    summary = service.learning_dashboard()

    assert summary["current_model"] == "NPI-v3"
    assert summary["training_samples"] == 1
    assert summary["candidate_models"] == 1
    assert summary["best_candidate"] == "NPI-v4"


def test_candidate_evaluation_can_include_backtest_gate():
    games = [
        {
            "actual_winner": "home",
            "predictions": {
                "NPI-v4": {"winner": "home", "confidence": 77.0},
            },
        }
    ]

    service = ModelTrainingService(
        dataset_service=_DatasetService(_dataset()),
        evaluation_service=_EvaluationService(),
        version_service=_VersionService("NPI-v3"),
        backtesting_service=_BacktestingService(),
    )

    service.train_candidate(version="NPI-v4")
    report = service.evaluate_candidate("NPI-v4", games=games)

    assert report["backtest"]["recommendation"] == "promote"
    assert service.candidates["NPI-v4"]["promotion_eligible"] is True