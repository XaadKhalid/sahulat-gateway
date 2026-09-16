from uuid import UUID

from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


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
