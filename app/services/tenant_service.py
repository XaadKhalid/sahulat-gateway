"""Tenant management for the admin console."""

from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.admin_tenants import (
    AdminDocumentRepository,
    AdminTenantRepository,
)
from app.schemas.admin import (
    DocumentList,
    DocumentRead,
    DocumentStatus,
    ManifestStatus,
    PolicyRead,
    TenantCreate,
    TenantDetail,
    TenantRead,
    TenantStatus,
    TenantUpdate,
)


class TenantService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
    ) -> None:
        self._sessions = sessions

    async def list_tenants(
        self, limit: int, cursor: UUID | None
    ) -> tuple[list[TenantRead], str | None]:

        async with self._sessions() as session:
            repo = AdminTenantRepository(session)
            rows, has_more = await repo.list(limit, cursor)
        items = [
            TenantRead(
                id=row["id"],
                name=row["name"],
                status=TenantStatus(row["status"]),
                whatsapp_connected=row["whatsapp_connected"],
                created_at=row["created_at"],
            )
            for row in rows[:limit]
        ]
        next_cursor = str(rows[-1]["id"]) if has_more else None
        return items, next_cursor

    async def get_tenant(self, tenant_id: UUID) -> TenantDetail | None:
        async with self._sessions() as session:
            repo = AdminTenantRepository(session)
            detail = await repo.get_detail(tenant_id)
        if detail is None:
            return None
        return self._to_detail(detail)

    async def create_tenant(self, payload: TenantCreate) -> TenantDetail:
        async with self._sessions() as session:
            repo = AdminTenantRepository(session)
            result = await repo.create(payload.name)
            detail = await repo.get_detail(UUID(str(result["id"])))
            await session.commit()
        assert detail is not None
        return self._to_detail(detail)

    async def update_tenant(
        self, tenant_id: UUID, payload: TenantUpdate
    ) -> TenantDetail | None:
        async with self._sessions() as session:
            repo = AdminTenantRepository(session)
            updated = await repo.update(tenant_id, payload.name, payload.policy)
            if updated is None:
                return None
            detail = await repo.get_detail(tenant_id)
            await session.commit()
        assert detail is not None
        return self._to_detail(detail)

    async def list_documents(
        self, tenant_id: UUID, limit: int, cursor: UUID | None
    ) -> DocumentList:
        async with self._sessions() as session:
            repo = AdminDocumentRepository(session)
            rows, has_more = await repo.list(tenant_id, limit, cursor)
        items = [
            DocumentRead(
                document_id=row["document_id"],
                filename=row["filename"],
                mime_type=row["mime_type"],
                status=DocumentStatus(row["status"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
        cursor_val = str(rows[-1]["document_id"]) if has_more else None
        return DocumentList(
            items=items,
            next_cursor=cursor_val,
        )

    async def upload_document(
        self,
        tenant_id: UUID,
        filename: str,
        mime_type: str,
        size_bytes: int,
    ) -> DocumentRead:
        async with self._sessions() as session:
            repo = AdminDocumentRepository(session)
            row = await repo.create(tenant_id, filename, mime_type, size_bytes)
            await session.commit()
        return DocumentRead(
            document_id=row["document_id"],
            filename=row["filename"],
            mime_type=row["mime_type"],
            status=DocumentStatus(row["status"]),
            created_at=row["created_at"],
        )

    async def delete_document(self, tenant_id: UUID, document_id: UUID) -> bool:
        async with self._sessions() as session:
            repo = AdminDocumentRepository(session)
            deleted = await repo.delete(tenant_id, document_id)
            await session.commit()
        return deleted

    def _to_detail(self, d: dict[str, Any]) -> TenantDetail:
        policy = cast(dict[str, Any], d["policy"] or {})
        return TenantDetail(
            id=d["id"],
            name=d["name"],
            status=TenantStatus(d["status"]),
            whatsapp_connected=d["whatsapp_connected"],
            created_at=d["created_at"],
            document_count=d["document_count"],
            manifest_status=ManifestStatus(d["manifest_status"]),
            policy=PolicyRead(**policy),
        )
