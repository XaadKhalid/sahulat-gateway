from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class TextContent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["text"] = "text"
    text: str = Field(min_length=1)


class UnsupportedContent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["unsupported"] = "unsupported"
    provider_kind: str = Field(min_length=1, max_length=128)


class MessageEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    session_id: UUID
    channel: Literal["whatsapp"] = "whatsapp"
    provider_message_id: str = Field(min_length=1, max_length=256)
    content: Annotated[TextContent | UnsupportedContent, Field(discriminator="kind")]
    occurred_at: AwareDatetime

    @field_validator("occurred_at")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class MessageSaveResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: MessageEnvelope
    created: bool
