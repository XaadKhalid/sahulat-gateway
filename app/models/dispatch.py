import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DispatchState(str, enum.Enum):
    PENDING = "pending"
    ENQUEUED = "enqueued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED_RETRY = "failed_retry"
    FAILED_TERMINAL = "failed_terminal"
    REVIEW_REQUIRED = "review_required"


class DispatchIntentRow(Base):
    __tablename__ = "dispatch_intents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "message_id"],
            ["sahulat.messages.tenant_id", "sahulat.messages.id"],
            name="dispatch_intent_message_fk",
        ),
        {"schema": "sahulat"},
    )

    tenant_id: Mapped[UUID] = mapped_column(primary_key=True)
    message_id: Mapped[UUID] = mapped_column(primary_key=True)

    state: Mapped[DispatchState] = mapped_column(
        Enum(
            DispatchState,
            name="dispatch_state_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        server_default="pending",
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
