import secrets
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import DatabaseSettings
from app.schemas.messages import MessageEnvelope, TextContent, UnsupportedContent


def test_envelope_normalizes_aware_timestamp_to_utc() -> None:
    message = MessageEnvelope(
        tenant_id=uuid4(),
        session_id=uuid4(),
        provider_message_id="test-message",
        content=TextContent(text="Hello"),
        occurred_at=datetime(2026, 9, 16, 12, tzinfo=timezone(timedelta(hours=5))),
    )
    assert message.occurred_at == datetime(2026, 9, 16, 7, tzinfo=UTC)
    assert message.occurred_at.tzinfo == UTC


def test_envelope_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        MessageEnvelope(
            tenant_id=uuid4(),
            session_id=uuid4(),
            provider_message_id="test-message",
            content=TextContent(text="Hello"),
            occurred_at=datetime(2026, 9, 16),
        )


def test_content_union_round_trips_unsupported_kind_without_media() -> None:
    message = MessageEnvelope(
        tenant_id=uuid4(),
        session_id=uuid4(),
        provider_message_id="test-message",
        content=UnsupportedContent(provider_kind="audio"),
        occurred_at=datetime.now(UTC),
    )
    assert MessageEnvelope.model_validate_json(message.model_dump_json()) == message


def test_database_url_is_required_and_not_printed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SAHULAT_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        DatabaseSettings()
    password = secrets.token_urlsafe(32)
    settings = DatabaseSettings(
        database_url=SecretStr(
            "postgresql+asyncpg://account:" + password + "@localhost/db"
        )
    )
    assert password not in repr(settings)
    assert password not in settings.model_dump_json()


def test_database_url_rejects_sync_driver_without_exposing_input() -> None:
    password = secrets.token_urlsafe(32)
    with pytest.raises(ValidationError) as error:
        DatabaseSettings(
            database_url=SecretStr("postgresql://account:" + password + "@localhost/db")
        )
    assert password not in str(error.value)
