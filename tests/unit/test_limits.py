from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.health import create_health_router
from app.api.limits import HealthRequestLimits


async def test_probe_rate_limit_recovers_after_window() -> None:
    now = 10.0
    application = FastAPI()
    limits = HealthRequestLimits(2, clock=lambda: now)
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
