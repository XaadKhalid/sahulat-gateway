from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


class AdminTenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, limit: int, cursor: UUID | None
    ) -> tuple[list[dict[str, Any]], bool]:
        stmt = text("SELECT * FROM sahulat_admin.list_tenants(:limit, :cursor)")
        rows = (
            await self._session.execute(
                stmt,
                {"limit": limit + 1, "cursor": str(cursor) if cursor else None},
            )
        ).fetchall()
        result = [dict(row._mapping) for row in rows]
        has_more = len(result) > limit
        return result[:limit], has_more

    async def get(self, tenant_id: UUID) -> dict[str, Any] | None:
        stmt = text("SELECT * FROM sahulat_admin.get_tenant_detail(:tenant_id)")
        row = (
            await self._session.execute(stmt, {"tenant_id": str(tenant_id)})
        ).fetchone()
        if row is None:
            return None
        d = dict(row._mapping)
        return {
            "id": d["id"],
            "name": d["name"],
            "status": d["status"],
            "whatsapp_connected": d["whatsapp_connected"],
            "created_at": d["created_at"],
        }

    async def get_detail(self, tenant_id: UUID) -> dict[str, Any] | None:
        stmt = text("SELECT * FROM sahulat_admin.get_tenant_detail(:tenant_id)")
        row = (
            await self._session.execute(stmt, {"tenant_id": str(tenant_id)})
        ).fetchone()
        if row is None:
            return None
        d = dict(row._mapping)
        return {
            "id": d["id"],
            "name": d["name"],
            "status": d["status"],
            "whatsapp_connected": d["whatsapp_connected"],
            "created_at": d["created_at"],
            "document_count": int(d["document_count"]),
            "manifest_status": d["manifest_status"],
            "policy": d["policy"],
        }

    async def create(self, name: str) -> dict[str, Any]:
        from app.models.tenants import TenantRow

        tenant_id = uuid4()
        await self._session.execute(
            text("SELECT set_config('sahulat.tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )
        row = TenantRow(
            id=tenant_id,
            name=name,
            status="draft",
            whatsapp_connected=False,
            manifest_status="pending",
            created_at=datetime.now(UTC),
            policy={
                "persona": "You are a helpful business assistant.",
                "languages": "en",
                "domain_fence": "same-origin",
                "refusal_style": "polite",
                "business_hours": "09:00-18:00",
                "verified_ttl_minutes": 60,
                "handoff_rules": "escalate",
            },
        )
        self._session.add(row)
        await self._session.flush()
        return {
            "id": row.id,
            "name": row.name,
            "status": row.status,
            "whatsapp_connected": row.whatsapp_connected,
            "created_at": row.created_at,
        }

    async def update(
        self, tenant_id: UUID, name: str | None, policy: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        from app.models.tenants import TenantRow

        await self._session.execute(
            text("SELECT set_config('sahulat.tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )
        row = await self._session.get(TenantRow, tenant_id)
        if row is None:
            return None
        if name is not None:
            row.name = name
        if policy is not None:
            existing = dict(row.policy or {})
            existing.update(policy)
            row.policy = existing
        await self._session.flush()
        return await self.get(tenant_id)


class AdminDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, tenant_id: UUID, limit: int, cursor: UUID | None
    ) -> tuple[list[dict[str, Any]], bool]:
        from app.models.documents import TenantDocumentRow

        stmt = (
            select(TenantDocumentRow)
            .where(TenantDocumentRow.tenant_id == tenant_id)
            .order_by(TenantDocumentRow.document_id)
        )
        if cursor is not None:
            stmt = stmt.where(TenantDocumentRow.document_id > cursor)
        rows = (await self._session.scalars(stmt)).unique().all()
        result = [
            {
                "document_id": r.document_id,
                "filename": r.filename,
                "mime_type": r.mime_type,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in rows
        ]
        has_more = len(result) > limit
        return result[:limit], has_more

    async def create(
        self, tenant_id: UUID, filename: str, mime_type: str, size_bytes: int
    ) -> dict[str, Any]:
        from app.models.documents import TenantDocumentRow

        doc_id = uuid4()
        row = TenantDocumentRow(
            tenant_id=tenant_id,
            document_id=doc_id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            status="processing",
        )
        self._session.add(row)
        await self._session.flush()
        return {
            "document_id": row.document_id,
            "filename": row.filename,
            "mime_type": row.mime_type,
            "status": row.status,
            "created_at": row.created_at,
        }

    async def delete(self, tenant_id: UUID, document_id: UUID) -> bool:
        from app.models.documents import TenantDocumentRow

        row = await self._session.get(
            TenantDocumentRow, {"tenant_id": tenant_id, "document_id": document_id}
        )
        if row is None:
            return False
        await self._session.delete(row)
        return True
