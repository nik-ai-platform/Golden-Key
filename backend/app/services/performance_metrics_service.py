from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return round(values[0], 2)

    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * ratio))
    index = max(0, min(index, len(ordered) - 1))
    return round(ordered[index], 2)


@dataclass
class _RequestMetric:
    path: str
    method: str
    status_code: int
    duration_ms: float
    recorded_at: float


class PerformanceMetricsService:
    def __init__(self):
        self._lock = Lock()
        self._requests: deque[_RequestMetric] = deque(maxlen=10000)
        self._prediction_latencies_ms: deque[float] = deque(maxlen=10000)
        self._scheduler_stage_latencies_ms: dict[str, deque[float]] = {}
        self._scheduler_stage_failures: dict[str, int] = {}
        self._auth_failures: deque[dict] = deque(maxlen=10000)
        self._db_query_latencies_ms: deque[float] = deque(maxlen=10000)
        self._worker_failures: dict[str, int] = {}
        self._pipeline_durations_ms: deque[float] = deque(maxlen=5000)

    def record_api_request(self, path: str, method: str, status_code: int, duration_ms: float):
        with self._lock:
            self._requests.append(
                _RequestMetric(
                    path=path,
                    method=method,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    recorded_at=monotonic(),
                )
            )

    def record_prediction_latency(self, duration_ms: float):
        with self._lock:
            self._prediction_latencies_ms.append(float(duration_ms))

    def record_scheduler_stage(self, stage_name: str, duration_ms: float, success: bool):
        with self._lock:
            bucket = self._scheduler_stage_latencies_ms.setdefault(
                stage_name,
                deque(maxlen=5000),
            )
            bucket.append(float(duration_ms))

            if not success:
                self._scheduler_stage_failures[stage_name] = self._scheduler_stage_failures.get(stage_name, 0) + 1

    def record_auth_failure(self, reason: str, subject: str, attempts: int = 0):
        with self._lock:
            self._auth_failures.append(
                {
                    "reason": reason,
                    "subject": subject,
                    "attempts": attempts,
                    "recorded_at": monotonic(),
                }
            )

    def record_db_query_latency(self, duration_ms: float):
        with self._lock:
            self._db_query_latencies_ms.append(float(duration_ms))

    def record_worker_failure(self, worker_name: str):
        with self._lock:
            self._worker_failures[worker_name] = self._worker_failures.get(worker_name, 0) + 1

    def record_pipeline_duration(self, duration_ms: float):
        with self._lock:
            self._pipeline_durations_ms.append(float(duration_ms))

    def snapshot(self):
        with self._lock:
            request_latencies = [item.duration_ms for item in self._requests]
            total_requests = len(self._requests)
            error_requests = sum(1 for item in self._requests if item.status_code >= 500)

            now = monotonic()
            recent_window_start = now - 60.0
            recent_predictions = [
                item
                for item in self._requests
                if item.path.startswith("/api/v1/predictions") and item.recorded_at >= recent_window_start
            ]

            scheduler_stages = {}
            for stage, values in self._scheduler_stage_latencies_ms.items():
                stage_values = list(values)
                scheduler_stages[stage] = {
                    "avg_ms": round(sum(stage_values) / len(stage_values), 2) if stage_values else 0.0,
                    "p95_ms": _percentile(stage_values, 0.95),
                    "runs": len(stage_values),
                    "failures": self._scheduler_stage_failures.get(stage, 0),
                }

            prediction_values = list(self._prediction_latencies_ms)
            db_values = list(self._db_query_latencies_ms)
            pipeline_values = list(self._pipeline_durations_ms)
            auth_failures = list(self._auth_failures)
            recent_auth_failures = [
                item for item in auth_failures if item["recorded_at"] >= recent_window_start
            ]

            return {
                "api": {
                    "request_count": total_requests,
                    "average_response_ms": round(sum(request_latencies) / total_requests, 2) if total_requests else 0.0,
                    "p95_response_ms": _percentile(request_latencies, 0.95),
                    "error_rate_percent": round((error_requests / total_requests) * 100, 2) if total_requests else 0.0,
                },
                "prediction": {
                    "average_generation_ms": round(sum(prediction_values) / len(prediction_values), 2) if prediction_values else 0.0,
                    "p95_generation_ms": _percentile(prediction_values, 0.95),
                    "throughput_per_minute": len(recent_predictions),
                },
                "database": {
                    "average_query_ms": round(sum(db_values) / len(db_values), 2) if db_values else 0.0,
                    "p95_query_ms": _percentile(db_values, 0.95),
                },
                "pipeline": {
                    "average_duration_ms": round(sum(pipeline_values) / len(pipeline_values), 2) if pipeline_values else 0.0,
                    "p95_duration_ms": _percentile(pipeline_values, 0.95),
                },
                "auth": {
                    "failures_per_minute": len(recent_auth_failures),
                    "total_failures": len(auth_failures),
                },
                "workers": {
                    "failures": dict(self._worker_failures),
                },
                "scheduler": scheduler_stages,
            }


performance_metrics = PerformanceMetricsService()