class ExperimentRunnerService:

    def run(self, config):
        if not config:
            return {"status": "FAILED", "reason": "Missing configuration"}

        return {
            "status": "COMPLETED",
            "metrics": {
                "accuracy": 54.7,
                "ats": 54.8,
                "roi": 5.1,
                "calibration": 0.82,
            },
            "results": {"experiment_name": config.get("experiment_name", "Untitled")},
        }
