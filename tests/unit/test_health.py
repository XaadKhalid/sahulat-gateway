from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("SAHULAT_HEALTH_REQUESTS_PER_SECOND", "10")
    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://test"
    ) as client:
        yield client


async def test_health_returns_only_process_liveness(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
async def test_documentation_is_not_public(client: AsyncClient, path: str) -> None:
    assert (await client.get(path)).status_code == 404


async def test_health_rejects_request_body(client: AsyncClient) -> None:
    response = await client.request("GET", "/health", content=b"unexpected")
    assert response.status_code == 413


async def test_health_rejects_streamed_body(client: AsyncClient) -> None:
    async def body() -> AsyncIterator[bytes]:
        yield b"unexpected"

    response = await client.request("GET", "/health", content=body())
    assert response.status_code == 413


async def test_health_rejects_post(client: AsyncClient) -> None:
    assert (await client.post("/health")).status_code == 405
