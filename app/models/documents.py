from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TenantDocumentRow(Base):
    __tablename__ = "tenant_documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'ready', 'failed')",
            name="doc_status_valid",
        ),
        CheckConstraint("length(filename) > 0", name="doc_filename_not_empty"),
        CheckConstraint("size_bytes > 0", name="doc_size_positive"),
        ForeignKeyConstraint(
            ["tenant_id"], ["sahulat.tenants.id"], name="doc_tenant_fk"
        ),
        {"schema": "sahulat"},
    )

    tenant_id: Mapped[UUID] = mapped_column(primary_key=True)
    document_id: Mapped[UUID] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
