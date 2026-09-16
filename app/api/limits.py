from collections.abc import Awaitable, Callable
from time import monotonic

from fastapi import Request, Response


class HealthRequestLimits:
    """Bound aggregate probe traffic per process without storing client PII."""

    def __init__(
        self, requests_per_second: int, clock: Callable[[], float] = monotonic
    ) -> None:
        self._limit = requests_per_second
        self._clock = clock
        self._window_start = clock()
        self._requests = 0

    def _permit_request(self) -> bool:
        now = self._clock()
        if now - self._window_start >= 1:
            self._window_start = now
            self._requests = 0
        if self._requests >= self._limit:
            return False
        self._requests += 1
        return True

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self._permit_request():
            return Response(status_code=429, headers={"Retry-After": "1"})
        # Health probes accept no request payload; never buffer an arbitrary body.
        if request.headers.get("content-length", "0") != "0":
            return Response(status_code=413)
        if "transfer-encoding" in request.headers:
            return Response(status_code=413)
        async for chunk in request.stream():
            if chunk:
                return Response(status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response
