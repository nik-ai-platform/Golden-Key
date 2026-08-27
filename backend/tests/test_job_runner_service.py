from app.services.job_runner_service import (
    JobRunnerService
)


def test_retry_success():

    service = JobRunnerService()


    result = service.run_with_retry(
        lambda: "success"
    )


    assert result == "success"


def test_retry_logs_exception_before_retry(monkeypatch):

    class _FakeMonitor:
        def __init__(self):
            self.calls = []

        def log_exception(self, message, **context):
            self.calls.append((message, context))

    attempts = {"count": 0}

    def job():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("boom")
        return "ok"

    fake_monitor = _FakeMonitor()
    service = JobRunnerService(monitor=fake_monitor)
    monkeypatch.setattr("app.services.job_runner_service.time.sleep", lambda *_: None)

    result = service.run_with_retry(job, retries=2, delay=0)

    assert result == "ok"
    assert len(fake_monitor.calls) == 1
    assert fake_monitor.calls[0][0] == "Job failed"
    assert fake_monitor.calls[0][1]["attempt"] == 1
