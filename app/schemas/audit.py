from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: UUID
    id: UUID
    occurred_at: datetime
    event_type: str = Field(min_length=1, max_length=100)
    actor: str = Field(min_length=1, max_length=100)
    details: dict[str, str | int | float | bool | None]
