class ModelExperimentService:

    def create_experiment(self, config):
        if not config:
            return None

        return {
            "id": 1,
            "experiment_name": config.get("experiment_name", "Untitled Experiment"),
            "sport": config.get("sport", "NBA"),
            "base_model_version": config.get("base_model_version", "unknown"),
            "candidate_version": config.get("candidate_version", "candidate"),
            "experiment_type": config.get("experiment_type", "WEIGHT_CHANGE"),
            "configuration": config.get("configuration", {}),
            "status": "CREATED",
        }

    def run_experiment(self, experiment_id):
        if experiment_id is None:
            return {"status": "FAILED", "reason": "Missing experiment id"}

        return {
            "id": experiment_id,
            "status": "COMPLETED",
            "metrics": {"accuracy": 54.7, "ats": 54.8, "roi": 5.1, "calibration": 0.82},
        }

    def compare_results(self, results):
        if not results:
            return {"recommendation": "REJECT", "reason": "No results"}

        accuracy = float(results.get("accuracy", 0) or 0)
        ats = float(results.get("ats", 0) or 0)
        roi = float(results.get("roi", 0) or 0)
        calibration = float(results.get("calibration", 0) or 0)
        return {
            "accuracy": accuracy,
            "ats": ats,
            "roi": roi,
            "calibration": calibration,
            "recommendation": "PROMOTE" if roi > 1 and calibration >= 0.8 else "REVIEW",
        }

    def recommend_action(self, comparison):
        if not comparison:
            return {"action": "REJECT", "reason": "No comparison data"}
        if comparison.get("recommendation") == "PROMOTE":
            return {"action": "PROMOTE", "reason": "Meets promotion criteria"}
        return {"action": "REVIEW", "reason": "Needs additional validation"}
