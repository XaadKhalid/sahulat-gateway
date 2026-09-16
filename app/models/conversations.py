from datetime import datetime
from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SessionRow(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "customer_number", name="session_customer_unique"
        ),
        CheckConstraint(
            "length(customer_number) > 0", name="session_customer_not_empty"
        ),
        {"schema": "sahulat"},
    )

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("sahulat.tenants.id"), primary_key=True
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    customer_number: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MessageRow(Base):
    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "session_id"],
            ["sahulat.sessions.tenant_id", "sahulat.sessions.id"],
            name="message_session_same_tenant",
        ),
        UniqueConstraint(
            "tenant_id", "provider_message_id", name="message_provider_unique"
        ),
        CheckConstraint("channel = 'whatsapp'", name="message_supported_channel"),
        CheckConstraint(
            "length(provider_message_id) > 0", name="message_provider_not_empty"
        ),
        CheckConstraint(
            "jsonb_typeof(content) = 'object'", name="message_content_object"
        ),
        {"schema": "sahulat"},
    )

    tenant_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID]
    channel: Mapped[str] = mapped_column(String(32))
    provider_message_id: Mapped[str] = mapped_column(String(256))
    content: Mapped[dict[str, JsonValue]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
