from datetime import UTC, datetime, timedelta
import hashlib

from app.models.training_dataset import TrainingDataset
from app.models.training_job import TrainingJob
from app.services.backtesting_service import BacktestingService
from app.services.model_evaluation_service import ModelEvaluationService
from app.services.model_version_service import ModelVersionService
from app.services.training_dataset_service import TrainingDatasetService


class ModelTrainingService:
    """Coordinates candidate model lifecycle without auto-promoting to production."""

    DEVELOPMENT = "Development"
    CANDIDATE = "Candidate"
    EVALUATING = "Evaluating"
    APPROVED = "Approved"
    PRODUCTION = "Production"
    RETIRED = "Retired"

    def __init__(
        self,
        dataset_service=None,
        evaluation_service=None,
        version_service=None,
        backtesting_service=None,
    ):
        self.dataset_service = dataset_service or TrainingDatasetService()
        self.evaluation_service = evaluation_service or ModelEvaluationService()
        self.version_service = version_service or ModelVersionService()
        self.backtesting_service = backtesting_service
        self.candidates = {}
        self.production_version = self.version_service.get_current_version()

    def build_dataset(self, sport="NBA", dataset_version="v1", game_count=120, feature_version="2.2", date_range=None, checksum=None, db=None):
        if checksum is None:
            checksum = hashlib.sha256(f"{sport}:{dataset_version}:{game_count}:{feature_version}".encode("utf-8")).hexdigest()
        dataset = TrainingDataset(
            sport=sport,
            dataset_version=dataset_version,
            game_count=game_count,
            feature_version=feature_version,
            date_range=date_range or "2024-01-01:2024-06-30",
            checksum=checksum,
        )
        return dataset

    def prepare_training_data(self, db=None, start_date=None, end_date=None):
        end = end_date or datetime.now(UTC)
        start = start_date or (end - timedelta(days=30))

        dataset = self.dataset_service.build_dataset(start, end, db=db)
        validation = self.dataset_service.validate_dataset(dataset)
        if not validation["valid"]:
            raise ValueError("Training dataset failed validation")

        return dataset

    def train_candidate(self, dataset=None, db=None, start_date=None, end_date=None, version=None, fail_training=False):
        if fail_training:
            raise ValueError("Training failed")

        records = dataset or self.prepare_training_data(db=db, start_date=start_date, end_date=end_date)
        candidate_version = version or self._next_version()

        self.candidates[candidate_version] = {
            "version": candidate_version,
            "status": self.CANDIDATE,
            "training_samples": len(records),
            "created_at": datetime.now(UTC).isoformat(),
            "evaluation": None,
            "promotion_eligible": False,
            "approved_by": None,
        }

        return self.candidates[candidate_version]

    def validate_candidate(self, candidate_version, validation_score=56.1):
        if candidate_version not in self.candidates:
            raise ValueError("Candidate model not found")
        candidate = self.candidates[candidate_version]
        candidate["validation_score"] = validation_score
        candidate["status"] = self.EVALUATING
        return candidate

    def store_model(self, candidate_version, version=None, sport="NBA", validation_score=56.1, roi=8.1, notes=None):
        if candidate_version not in self.candidates:
            raise ValueError("Candidate model not found")
        candidate = self.candidates[candidate_version]
        candidate["stored_version"] = version or candidate_version
        candidate["validation_score"] = validation_score
        candidate["roi"] = roi
        candidate["notes"] = notes or "stored"
        return candidate

    def evaluate_candidate(self, candidate_version, games, current_version=None):
        if candidate_version not in self.candidates:
            raise ValueError("Candidate model not found")

        current = current_version or self.version_service.get_current_version()
        candidate = self.candidates[candidate_version]
        candidate["status"] = self.EVALUATING

        current_metric = self.evaluation_service.evaluate_model(current, games)
        candidate_metric = self.evaluation_service.evaluate_model(candidate_version, games)
        comparison = self.evaluation_service.compare_models(current_metric, candidate_metric)

        backtest_report = None
        if self.backtesting_service is not None:
            candidate_predictions = self.backtesting_service.simulate_predictions(
                games,
                candidate_version,
                model_version=candidate_version,
            )
            candidate_results = self.backtesting_service.calculate_results(candidate_predictions)
            backtest_report = self.backtesting_service.generate_report(candidate_results)

        report = {
            "current_version": current,
            "candidate_version": candidate_version,
            "comparison": comparison.model_dump(),
            "recommendation": comparison.winner,
            "backtest": backtest_report,
        }

        candidate["evaluation"] = report
        candidate["promotion_eligible"] = (
            comparison.winner == "candidate"
            and (backtest_report is None or backtest_report["recommendation"] == "promote")
        )
        candidate["status"] = self.APPROVED if candidate["promotion_eligible"] else self.CANDIDATE

        return report

    def evaluate_candidate_models(self, games):
        reports = []

        for version, info in self.candidates.items():
            if info["status"] == self.RETIRED:
                continue
            reports.append(
                self.evaluate_candidate(
                    candidate_version=version,
                    games=games,
                )
            )

        return reports

    def submit_for_review(self, candidate_version, admin_approved=False, approved_by=None):
        if candidate_version not in self.candidates:
            raise ValueError("Candidate model not found")

        candidate = self.candidates[candidate_version]
        if not candidate.get("promotion_eligible"):
            raise PermissionError("Candidate cannot bypass evaluation")

        if not admin_approved:
            return {
                "version": candidate_version,
                "status": candidate["status"],
                "deployed": False,
                "reason": "Admin approval required",
            }

        previous = self.production_version
        if previous in self.candidates:
            self.candidates[previous]["status"] = self.RETIRED

        candidate["status"] = self.PRODUCTION
        candidate["approved_by"] = approved_by or "admin"
        self.production_version = candidate_version
        self.version_service.set_current_version(candidate_version)

        return {
            "version": candidate_version,
            "status": candidate["status"],
            "deployed": True,
            "retired": previous,
        }

    def learning_dashboard(self):
        active_candidates = [
            info for info in self.candidates.values() if info["status"] != self.RETIRED
        ]

        best = None
        best_accuracy = -1.0

        for info in active_candidates:
            comparison = (info.get("evaluation") or {}).get("comparison") or {}
            accuracy = ((comparison.get("candidate_model") or {}).get("accuracy"))
            if isinstance(accuracy, (int, float)) and accuracy > best_accuracy:
                best = info["version"]
                best_accuracy = float(accuracy)

        return {
            "current_model": self.version_service.get_current_version(),
            "training_samples": sum(info.get("training_samples", 0) for info in active_candidates),
            "candidate_models": len(active_candidates),
            "best_candidate": best,
        }

    def _next_version(self):
        current = self.version_service.get_current_version()
        prefix = "NPI-v"

        if not current.startswith(prefix):
            return "NPI-v1"

        try:
            number = int(current.replace(prefix, ""))
        except ValueError:
            return "NPI-v1"

        return f"{prefix}{number + 1}"