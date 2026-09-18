from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AdminSessionRow, AdminUserRow
from app.schemas.admin import UserRole


class AdminUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, limit: int, cursor: UUID | None
    ) -> tuple[list[AdminUserRow], bool]:
        stmt = (
            select(AdminUserRow)
            .where(AdminUserRow.deactivated_at.is_(None))
            .order_by(AdminUserRow.id)
        )
        if cursor is not None:
            stmt = stmt.where(AdminUserRow.id > cursor)
        rows = (await self._session.scalars(stmt)).all()
        has_more = len(rows) > limit
        result: list[AdminUserRow] = list(rows[:limit])
        return result, has_more

    async def get(self, user_id: UUID) -> AdminUserRow | None:
        return await self._session.get(AdminUserRow, user_id)

    async def get_by_email(self, email: str) -> AdminUserRow | None:
        stmt = select(AdminUserRow).where(
            AdminUserRow.email == email,
            AdminUserRow.deactivated_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        email: str,
        role: UserRole,
        display_name: str,
        password_hash: str | None = None,
    ) -> AdminUserRow:
        row = AdminUserRow(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            role=role.value,
            display_name=display_name,
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_role(self, user_id: UUID, role: UserRole) -> AdminUserRow | None:
        stmt = (
            update(AdminUserRow)
            .where(AdminUserRow.id == user_id)
            .values(role=role.value)
        )
        await self._session.execute(stmt)
        return await self.get(user_id)

    async def deactivate(self, user_id: UUID, now: datetime) -> bool:
        user = await self._session.get(AdminUserRow, user_id)
        if user is None or user.deactivated_at is not None:
            return False
        user.deactivated_at = now
        return True

    async def admin_count(self) -> int:
        stmt = (
            select(func.count())
            .select_from(AdminUserRow)
            .where(
                AdminUserRow.role == "admin",
                AdminUserRow.deactivated_at.is_(None),
            )
        )
        count = await self._session.scalar(stmt)
        return int(count) if count else 0


class AdminSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: UUID, ttl: timedelta) -> AdminSessionRow:
        now = datetime.now(UTC)
        row = AdminSessionRow(
            session_id=uuid4(),
            user_id=user_id,
            issued_at=now,
            expires_at=now + ttl,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_active(
        self, session_id: UUID, now: datetime
    ) -> AdminSessionRow | None:
        stmt = select(AdminSessionRow).where(
            AdminSessionRow.session_id == session_id,
            AdminSessionRow.expires_at > now,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def revoke(self, session_id: UUID) -> None:
        stmt = delete(AdminSessionRow).where(AdminSessionRow.session_id == session_id)
        await self._session.execute(stmt)

    async def purge_expired(self, now: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(AdminSessionRow)
            .where(AdminSessionRow.expires_at <= now)
        )
        count = await self._session.scalar(stmt)
        if count:
            delete_stmt = delete(AdminSessionRow).where(
                AdminSessionRow.expires_at <= now
            )
            await self._session.execute(delete_stmt)
        return int(count or 0)
