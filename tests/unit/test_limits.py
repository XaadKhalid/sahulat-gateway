from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.health import create_health_router
from app.api.limits import GatewayRequestLimits


def _clock() -> float:
    return 100.0


def test_limits_permit_traffic_below_threshold() -> None:
    limits = GatewayRequestLimits(health_limit=10, webhook_limit=100, clock=_clock)
    for _ in range(10):
        assert limits._permit_health() is True
    assert limits._permit_health() is False


async def test_probe_rate_limit_recovers_after_window() -> None:
    now = 10.0
    application = FastAPI()
    limits = GatewayRequestLimits(health_limit=2, webhook_limit=2, clock=lambda: now)
    application.middleware("http")(limits.dispatch)
    application.include_router(create_health_router())
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        assert (await client.get("/health")).status_code == 200
        assert (await client.get("/health")).status_code == 200
        rejected = await client.get("/health")
        assert rejected.status_code == 429
        assert rejected.headers["retry-after"] == "1"
        now += 1
        assert (await client.get("/health")).status_code == 200
