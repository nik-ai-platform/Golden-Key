from app.services.job_runner_service import (
    JobRunnerService
)


class JobScheduler:

    def __init__(
        self,
        runner=None,
    ):

        self.runner = runner or JobRunnerService()

    def run_import_job(self):

        self.runner.run_with_retry(
            self.import_games
        )
