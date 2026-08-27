from __future__ import annotations

import asyncio
from collections import deque
from time import monotonic

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings


class SecurityMiddleware:
    def __init__(self) -> None:
        self._request_windows: dict[str, deque[float]] = {}

    def _rate_limit_key(self, request: Request) -> str:
        client_ip = request.client.host if request.client else "unknown"
        return f"{client_ip}:{request.url.path}"

    def _allow_request(self, key: str) -> bool:
        now = monotonic()
        window_start = now - 60.0
        bucket = self._request_windows.setdefault(key, deque())
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= settings.RATE_LIMIT_PER_MINUTE + settings.RATE_LIMIT_BURST:
            return False

        bucket.append(now)
        return True

    async def guard(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > settings.MAX_REQUEST_BYTES:
                    return JSONResponse(status_code=413, content={"detail": "Request body too large"})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid content-length header"})

        key = self._rate_limit_key(request)
        if not self._allow_request(key):
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

        try:
            response = await asyncio.wait_for(call_next(request), timeout=settings.REQUEST_TIMEOUT_SECONDS)
        except TimeoutError:
            return JSONResponse(status_code=504, content={"detail": "Request timeout"})

        response.headers["X-API-Version"] = "v1"
        return response


security_middleware = SecurityMiddleware()
