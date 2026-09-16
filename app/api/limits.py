from collections.abc import Awaitable, Callable
from time import monotonic

from fastapi import Request, Response


class GatewayRequestLimits:
    """Bound aggregate traffic and enforce payload size limits per route."""

    def __init__(
        self,
        health_limit: int,
        webhook_limit: int,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._health_limit = health_limit
        self._webhook_limit = webhook_limit
        self._clock = clock
        self._window_start = clock()
        self._health_requests = 0
        self._webhook_requests = 0

    def _permit_health(self) -> bool:
        now = self._clock()
        if now - self._window_start >= 1:
            self._window_start = now
            self._health_requests = 0
            self._webhook_requests = 0
        if self._health_requests >= self._health_limit:
            return False
        self._health_requests += 1
        return True

    def _permit_webhook(self) -> bool:
        now = self._clock()
        if now - self._window_start >= 1:
            self._window_start = now
            self._health_requests = 0
            self._webhook_requests = 0
        if self._webhook_requests >= self._webhook_limit:
            return False
        self._webhook_requests += 1
        return True

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        is_health = request.url.path.startswith("/health")

        if is_health:
            if not self._permit_health():
                return Response(status_code=429, headers={"Retry-After": "1"})
            # Health probes accept no request payload; never buffer an arbitrary body.
            if (
                request.headers.get("content-length", "0") != "0"
                or "transfer-encoding" in request.headers
            ):
                return Response(status_code=413)
        else:
            if not self._permit_webhook():
                return Response(status_code=429, headers={"Retry-After": "1"})
            # Webhooks accept up to 1MB JSON.
            content_length = int(request.headers.get("content-length", "0"))
            if content_length > 1024 * 1024:
                return Response(status_code=413)

        response = await call_next(request)
        if is_health:
            response.headers["Cache-Control"] = "no-store"
        return response
