import hashlib
import hmac
import json
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import create_app
from app.models.audit import AuditRow
from app.models.conversations import MessageRow
from app.models.dispatch import DispatchIntentRow
from tests.integration.conftest import Database


@pytest.fixture
async def client(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv(
        "SAHULAT_DATABASE_URL",
        database.runtime.url.render_as_string(hide_password=False),
    )
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


async def test_ingress_processes_valid_message_atomically(
    database: Database, client: AsyncClient
) -> None:
    # 1. Prepare valid WhatsApp webhook payload
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "123456",
                                "phone_number_id": "789",
                            },
                            "messages": [
                                {
                                    "from": "987654321",
                                    "id": "wamid.XYZ123",
                                    "timestamp": "1672531200",
                                    "type": "text",
                                    "text": {"body": "Hello world!"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    expected_mac = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    # 2. Post to ingress
    response = await client.post(
        "/webhooks/whatsapp/route-a",
        content=body,
        headers={"X-Hub-Signature-256": f"sha256={expected_mac}"},
    )
    assert response.status_code == 200

    # 3. Verify database state
    async with database.owner.begin() as conn:
        # Message inserted
        messages = (
            await conn.execute(
                select(MessageRow).where(MessageRow.tenant_id == database.tenant_a)
            )
        ).all()
        assert len(messages) == 1
        assert messages[0].provider_message_id == "wamid.XYZ123"

        # Audit inserted
        audits = (
            await conn.execute(
                select(AuditRow).where(AuditRow.tenant_id == database.tenant_a)
            )
        ).all()
        assert len(audits) == 1
        assert audits[0].event_type == "message.received"

        # Dispatch intent inserted
        dispatches = (
            await conn.execute(
                select(DispatchIntentRow).where(
                    DispatchIntentRow.tenant_id == database.tenant_a
                )
            )
        ).all()
        assert len(dispatches) == 1
        assert dispatches[0].message_id == messages[0].id


async def test_ingress_idempotency_on_duplicate(
    database: Database, client: AsyncClient
) -> None:
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "123",
                                "phone_number_id": "456",
                            },
                            "messages": [
                                {
                                    "from": "111",
                                    "id": "wamid.DUPLICATE",
                                    "timestamp": "1672531200",
                                    "type": "text",
                                    "text": {"body": "Echo"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    expected_mac = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    # First request
    response1 = await client.post(
        "/webhooks/whatsapp/route-b",
        content=body,
        headers={"X-Hub-Signature-256": f"sha256={expected_mac}"},
    )
    assert response1.status_code == 200

    # Second request
    response2 = await client.post(
        "/webhooks/whatsapp/route-b",
        content=body,
        headers={"X-Hub-Signature-256": f"sha256={expected_mac}"},
    )
    assert response2.status_code == 200

    async with database.owner.begin() as conn:
        messages = (
            await conn.execute(
                select(MessageRow).where(MessageRow.tenant_id == database.tenant_b)
            )
        ).all()
        assert len(messages) == 1

        # Dispatch intent uses ON CONFLICT DO NOTHING, so it remains 1
        dispatches = (
            await conn.execute(
                select(DispatchIntentRow).where(
                    DispatchIntentRow.tenant_id == database.tenant_b
                )
            )
        ).all()
        assert len(dispatches) == 1
