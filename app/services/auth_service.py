from datetime import UTC, datetime
from uuid import UUID

from passlib.context import CryptContext  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.admin_config import AdminSettings, session_ttl
from app.repositories.admin_users import AdminSessionRepository, AdminUserRepository
from app.schemas.admin import MeResponse, UserRole

_pwd_context: CryptContext = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return str(_pwd_context.hash(plain))


def verify_password(plain: str, hashed: str) -> bool:
    try:
        result = _pwd_context.verify(plain, hashed)
        return bool(result)
    except ValueError:
        return False


class AuthService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        admin_settings: AdminSettings,
    ) -> None:
        self._sessions = sessions
        self._ttl = session_ttl(admin_settings)

    async def login(self, email: str, password: str) -> tuple[MeResponse, str] | None:
        async with self._sessions() as session:
            user_repo = AdminUserRepository(session)
            user = await user_repo.get_by_email(email)
            if user is None or user.deactivated_at is not None:
                return None
            if user.password_hash is None or not verify_password(
                password, user.password_hash
            ):
                return None
            me = MeResponse(id=user.id, email=user.email, role=UserRole(user.role))
            session_repo = AdminSessionRepository(session)
            db_session = await session_repo.create(user.id, self._ttl)
            await session.commit()
            return me, str(db_session.session_id)

    async def logout(self, session_id: UUID) -> None:
        async with self._sessions() as session:
            await AdminSessionRepository(session).revoke(session_id)
            await session.commit()

    async def get_current(self, session_id: UUID) -> MeResponse | None:
        now = datetime.now(UTC)
        async with self._sessions() as session:
            session_repo = AdminSessionRepository(session)
            db_session = await session_repo.get_active(session_id, now)
            if db_session is None:
                return None
            user = await AdminUserRepository(session).get(db_session.user_id)
            if user is None or user.deactivated_at is not None:
                return None
            return MeResponse(id=user.id, email=user.email, role=UserRole(user.role))

    async def purge_expired_tokens(self) -> int:
        now = datetime.now(UTC)
        async with self._sessions() as session:
            count = await AdminSessionRepository(session).purge_expired(now)
            await session.commit()
            return count
