from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Callable


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.1
    backoff_multiplier: float = 2.0


class RetryService:
    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self.policy = policy or RetryPolicy()

    def _is_retryable(self, error: Exception) -> bool:
        message = str(error).lower()
        if "invalid data" in message:
            return False
        if "network" in message or "temporary" in message or "database unavailable" in message:
            return True
        return False

    def run_with_retry(self, action: Callable[[], object]) -> object:
        delay = self.policy.base_delay_seconds
        last_error: Exception | None = None

        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                return action()
            except Exception as error:  # noqa: BLE001
                last_error = error
                if not self._is_retryable(error):
                    raise
                if attempt == self.policy.max_attempts:
                    break
                sleep(delay)
                delay *= self.policy.backoff_multiplier

        assert last_error is not None
        raise last_error
