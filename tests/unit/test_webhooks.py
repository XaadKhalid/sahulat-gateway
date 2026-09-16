import hashlib
import hmac
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


async def test_webhook_verify_endpoint_success(client: AsyncClient) -> None:
    response = await client.get(
        "/webhooks/whatsapp?hub.mode=subscribe&hub.challenge=123&hub.verify_token=test-token"
    )
    assert response.status_code == 200
    assert response.text == "123"


async def test_webhook_verify_endpoint_failure(client: AsyncClient) -> None:
    response = await client.get(
        "/webhooks/whatsapp?hub.mode=subscribe&hub.challenge=123&hub.verify_token=wrong"
    )
    assert response.status_code == 403


async def test_webhook_receive_signature_missing(client: AsyncClient) -> None:
    response = await client.post("/webhooks/whatsapp/route-key", json={})
    assert response.status_code == 401


async def test_webhook_receive_signature_invalid(client: AsyncClient) -> None:
    response = await client.post(
        "/webhooks/whatsapp/route-key",
        json={},
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )
    assert response.status_code == 401


async def test_webhook_receive_signature_valid_but_bad_payload(
    client: AsyncClient,
) -> None:
    body = b"{}"
    expected_mac = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    response = await client.post(
        "/webhooks/whatsapp/route-key",
        content=body,
        headers={"X-Hub-Signature-256": f"sha256={expected_mac}"},
    )
    assert response.status_code == 422
