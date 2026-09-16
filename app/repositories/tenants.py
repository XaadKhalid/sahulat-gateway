from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenants import TenantRow
from app.schemas.tenants import RouteLookup, Tenant, TenantRoute


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, tenant_id: UUID) -> Tenant | None:
        row = await self._session.scalar(
            select(TenantRow).where(TenantRow.id == tenant_id)
        )
        return None if row is None else Tenant.model_validate(row)

    async def resolve(self, lookup: RouteLookup) -> TenantRoute | None:
        tenant_id = await self._session.scalar(
            text("SELECT sahulat.resolve_tenant_route(:route_key)"),
            {"route_key": lookup.route_key},
        )
        return None if tenant_id is None else TenantRoute(tenant_id=tenant_id)
