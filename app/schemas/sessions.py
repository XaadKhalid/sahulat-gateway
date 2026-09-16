from datetime import UTC, datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class SessionIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: UUID
    customer_number: str = Field(min_length=1, max_length=64)


class ConversationSession(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    tenant_id: UUID
    customer_number: str
    created_at: AwareDatetime

    @field_validator("created_at")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)
