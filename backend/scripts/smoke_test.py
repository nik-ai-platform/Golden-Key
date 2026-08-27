"""Run public API smoke checks against a live Golden Key backend."""

import os
import sys

import requests


BASE_URL = os.getenv("GOLDEN_KEY_API_URL", "http://127.0.0.1:8000").rstrip("/")
ENDPOINTS = (
    ("Health", "/health"),
    ("Readiness", "/api/v1/readiness"),
    ("API version", "/api/v1/version"),
    ("Today's predictions", "/api/v1/product/predictions/today"),
    ("Performance", "/api/v1/product/performance"),
)


def main() -> int:
    for label, endpoint in ENDPOINTS:
        url = f"{BASE_URL}{endpoint}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"FAIL {endpoint}: {error}", file=sys.stderr)
            return 1
        print(f"{label}: {response.status_code}")

    print("Golden Key API smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
