from app.services.retry_service import RetryPolicy, RetryService


def test_retry_service_retries_temporary_failures_then_succeeds():
    service = RetryService(policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.0, backoff_multiplier=1.0))
    attempts = {"count": 0}

    def flaky_action():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary network issue")
        return "ok"

    result = service.run_with_retry(flaky_action)
    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_service_does_not_retry_invalid_data():
    service = RetryService(policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.0, backoff_multiplier=1.0))

    def invalid_action():
        raise RuntimeError("invalid data format")

    try:
        service.run_with_retry(invalid_action)
        assert False, "Expected RuntimeError"
    except RuntimeError as error:
        assert "invalid data" in str(error)
