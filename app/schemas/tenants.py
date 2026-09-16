from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Tenant(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    name: str = Field(min_length=1, max_length=200)


class TenantRoute(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: UUID


class RouteLookup(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    route_key: str = Field(min_length=1, max_length=256)
