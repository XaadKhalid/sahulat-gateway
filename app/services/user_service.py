from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import PersistenceFailure
from app.models.admin import AdminUserRow
from app.repositories.admin_users import AdminUserRepository
from app.schemas.admin import UserCreate, UserRead, UserRole, UserUpdateRole
from app.services.auth_service import hash_password


class AdminUserError(ValueError):
    """Raised when a user-management business rule is violated."""


class UserService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def list_users(
        self, limit: int, cursor: UUID | None
    ) -> tuple[list[UserRead], str | None]:
        async with self._sessions() as session:
            repo = AdminUserRepository(session)
            rows, has_more = await repo.list(limit, cursor)
            items = [self._to_read(row) for row in rows]
            next_cursor: str | None = None
            if has_more and items:
                next_cursor = str(items[-1].id)
            return items, next_cursor

    async def get_user(self, user_id: UUID) -> UserRead | None:
        async with self._sessions() as session:
            row = await AdminUserRepository(session).get(user_id)
            return None if row is None else self._to_read(row)

    async def create_user(self, payload: UserCreate) -> UserRead:
        display_name = payload.display_name
        if display_name is None:
            local = payload.email.split("@", 1)[0]
            display_name = local.title()
        password_hash = hash_password(payload.password) if payload.password else None
        async with self._sessions() as session:
            repo = AdminUserRepository(session)
            existing = await repo.get_by_email(payload.email)
            if existing is not None:
                raise AdminUserError("A user with this email already exists.")
            row = await repo.create(
                email=payload.email,
                role=payload.role,
                display_name=display_name,
                password_hash=password_hash,
            )
            await session.commit()
            return self._to_read(row)

    async def update_role(
        self, user_id: UUID, payload: UserUpdateRole, current_user_id: UUID
    ) -> UserRead:
        async with self._sessions() as session:
            repo = AdminUserRepository(session)
            user = await repo.get(user_id)
            if user is None or user.deactivated_at is not None:
                raise AdminUserError("User not found.")
            if payload.role == UserRole.admin:
                updated = await repo.update_role(user_id, payload.role)
                await session.commit()
                if updated is None:
                    raise AdminUserError("User not found.")
                return self._to_read(updated)
            if user_id == current_user_id:
                count = await repo.admin_count()
                if count <= 1:
                    raise AdminUserError(
                        "You are the only remaining admin. Assign this "
                        "role to another user first."
                    )
            updated = await repo.update_role(user_id, payload.role)
            await session.commit()
            if updated is None:
                raise AdminUserError("User not found.")
            return self._to_read(updated)

    async def deactivate_user(self, user_id: UUID, current_user_id: UUID) -> None:
        if user_id == current_user_id:
            raise AdminUserError("You cannot deactivate your own account.")
        now = datetime.now(UTC)
        async with self._sessions() as session:
            repo = AdminUserRepository(session)
            user = await repo.get(user_id)
            if user is None or user.deactivated_at is not None:
                raise AdminUserError("User not found.")
            if user.role == UserRole.admin:
                count = await repo.admin_count()
                if count <= 1:
                    raise AdminUserError("Cannot deactivate the last remaining admin.")
            deactivated = await repo.deactivate(user_id, now)
            await session.commit()
            if not deactivated:
                raise PersistenceFailure("Could not deactivate user.")

    @staticmethod
    def _to_read(row: AdminUserRow) -> UserRead:
        return UserRead(
            id=row.id,
            email=row.email,
            role=UserRole(row.role),
            created_at=row.created_at,
            display_name=row.display_name,
            deactivated=row.deactivated_at is not None,
        )
