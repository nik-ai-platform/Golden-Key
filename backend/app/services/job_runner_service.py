import time

from app.services.monitoring_service import MonitoringService


class JobRunnerService:
    """
    Executes background jobs safely.
    """


    def __init__(
        self,
        monitor=None,
    ):
        self.monitor = monitor or MonitoringService()


    def run_with_retry(
        self,
        job,
        retries=3,
        delay=2
    ):

        attempt = 0


        while attempt < retries:

            try:

                result = job()

                return result


            except Exception as error:

                attempt += 1


                self.monitor.log_exception(
                    "Job failed",
                    attempt=attempt,
                    retries=retries,
                    error=error
                )


                if attempt >= retries:

                    raise


                time.sleep(
                    delay
                )
