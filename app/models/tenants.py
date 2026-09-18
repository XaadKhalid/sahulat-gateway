from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TenantRow(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint("length(name) > 0", name="tenant_name_not_empty"),
        CheckConstraint(
            "status IN ('draft', 'connecting', 'live', 'suspended')",
            name="tenant_status_valid",
        ),
        CheckConstraint(
            "manifest_status IN ('pending', 'present', 'invalid')",
            name="tenant_manifest_status_valid",
        ),
        {"schema": "sahulat"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    whatsapp_connected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    manifest_status: Mapped[str] = mapped_column(String(20), nullable=False)
    policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
