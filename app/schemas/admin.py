"""Schemas for admin API boundaries — no app or I/O dependencies."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(StrEnum):
    admin = "admin"
    operator = "operator"


class LoginRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1)


class MeResponse(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    email: EmailStr
    role: UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    email: EmailStr
    role: UserRole
    created_at: datetime
    display_name: str = Field(min_length=1, max_length=200)
    deactivated: bool = False


class UserCreate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: EmailStr
    role: UserRole
    password: str | None = Field(default=None, min_length=8)
    display_name: str | None = Field(default=None, min_length=1, max_length=200)


class UserUpdateRole(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: UserRole


class UserList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[UserRead]
    next_cursor: str | None = None


class TenantStatus(StrEnum):
    draft = "draft"
    connecting = "connecting"
    live = "live"
    suspended = "suspended"


class ManifestStatus(StrEnum):
    pending = "pending"
    present = "present"
    invalid = "invalid"


class DocumentStatus(StrEnum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class TenantRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    name: str = Field(min_length=1, max_length=200)
    status: TenantStatus
    whatsapp_connected: bool
    created_at: datetime


class TenantCreate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)


class TenantUpdate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    policy: dict[str, object] | None = None


class PolicyRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    persona: str = Field(min_length=1)
    languages: str = Field(default="en")
    domain_fence: str = Field(default="same-origin")
    refusal_style: str = Field(default="polite")
    business_hours: str = Field(default="09:00-18:00")
    verified_ttl_minutes: int = Field(default=60, ge=1)
    handoff_rules: str = Field(default="escalate")


class TenantDetail(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    name: str
    status: TenantStatus
    whatsapp_connected: bool
    created_at: datetime
    document_count: int = Field(ge=0)
    manifest_status: ManifestStatus
    policy: PolicyRead


class DocumentRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    document_id: UUID
    filename: str
    mime_type: str
    status: DocumentStatus
    created_at: datetime


class DocumentList(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[DocumentRead]
    next_cursor: str | None = None
