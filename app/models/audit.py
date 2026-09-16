from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditRow(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("length(event_type) > 0", name="audit_event_type_not_empty"),
        CheckConstraint("length(actor) > 0", name="audit_actor_not_empty"),
        CheckConstraint(
            "jsonb_typeof(details) = 'object'", name="audit_details_object"
        ),
        {
            "schema": "sahulat",
            "postgresql_partition_by": "RANGE (occurred_at)",
        },
    )

    tenant_id: Mapped[UUID] = mapped_column(primary_key=True)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    event_type: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict[str, object]] = mapped_column(JSONB)
