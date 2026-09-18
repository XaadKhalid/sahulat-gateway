from uuid import UUID, uuid4

import pytest

from app.core.admin_config import AdminSettings
from app.schemas.admin import UserRole
from app.services.auth_service import AuthService
from app.services.user_service import AdminUserError, UserService
from tests.integration.conftest import (
    ADMIN_CREDENTIALS,
    OPERATOR_CREDENTIALS,
    Database,
)


@pytest.fixture
def admin_settings() -> AdminSettings:
    return AdminSettings()


@pytest.fixture
def auth_service(database: Database, admin_settings: AdminSettings) -> AuthService:
    return AuthService(database.sessions, admin_settings)


@pytest.fixture
def user_service(database: Database) -> UserService:
    return UserService(database.sessions)


# ---------------------------------------------------------------------------
# AuthService
# ---------------------------------------------------------------------------


async def test_login_succeeds_with_valid_credentials(
    auth_service: AuthService,
) -> None:
    result = await auth_service.login(
        ADMIN_CREDENTIALS.email, ADMIN_CREDENTIALS.password
    )
    assert result is not None
    me, session_id = result
    assert me.email == ADMIN_CREDENTIALS.email
    assert me.role == UserRole.admin
    assert UUID(session_id)


async def test_login_fails_with_wrong_password(
    auth_service: AuthService,
) -> None:
    result = await auth_service.login(ADMIN_CREDENTIALS.email, "wrong-password")
    assert result is None


async def test_login_fails_with_unknown_email(
    auth_service: AuthService,
) -> None:
    result = await auth_service.login("nobody@acme.com", "password")
    assert result is None


async def test_get_current_returns_user_for_valid_session(
    auth_service: AuthService,
) -> None:
    result = await auth_service.login(
        ADMIN_CREDENTIALS.email, ADMIN_CREDENTIALS.password
    )
    assert result is not None
    _, session_id = result
    me = await auth_service.get_current(UUID(session_id))
    assert me is not None
    assert me.email == ADMIN_CREDENTIALS.email


async def test_get_current_returns_none_for_unknown_session(
    auth_service: AuthService,
) -> None:
    me = await auth_service.get_current(uuid4())
    assert me is None


async def test_logout_revokes_session(
    auth_service: AuthService,
) -> None:
    result = await auth_service.login(
        OPERATOR_CREDENTIALS.email, OPERATOR_CREDENTIALS.password
    )
    assert result is not None
    _, session_id = result
    assert await auth_service.get_current(UUID(session_id)) is not None
    await auth_service.logout(UUID(session_id))
    assert await auth_service.get_current(UUID(session_id)) is None


# ---------------------------------------------------------------------------
# UserService
# ---------------------------------------------------------------------------


async def test_list_users_returns_seeded_admins(
    user_service: UserService,
) -> None:
    items, cursor = await user_service.list_users(50, None)
    emails = [u.email for u in items]
    assert ADMIN_CREDENTIALS.email in emails
    assert OPERATOR_CREDENTIALS.email in emails
    assert cursor is None  # only 2 users, no next page


async def test_create_user_without_password_creates_invite(
    user_service: UserService,
) -> None:
    from app.schemas.admin import UserCreate

    user = await user_service.create_user(
        UserCreate(email="new@acme.com", role=UserRole.operator)
    )
    assert user.email == "new@acme.com"
    assert user.role == UserRole.operator
    assert user.display_name == "New"
    assert user.deactivated is False


async def test_create_user_with_password_sets_hash(
    user_service: UserService,
) -> None:
    from app.schemas.admin import UserCreate

    user = await user_service.create_user(
        UserCreate(
            email="pwd@acme.com",
            role=UserRole.admin,
            password="p@ssw0rd!",
            display_name="Pwd User",
        )
    )
    assert user.email == "pwd@acme.com"
    assert user.role == UserRole.admin


async def test_create_user_duplicate_email_raises(
    user_service: UserService,
) -> None:
    from app.schemas.admin import UserCreate

    with pytest.raises(AdminUserError, match="already exists"):
        await user_service.create_user(
            UserCreate(
                email=ADMIN_CREDENTIALS.email,
                role=UserRole.operator,
            )
        )


async def test_update_role_non_admin_cannot_demote_self(
    user_service: UserService, database: Database
) -> None:
    from app.schemas.admin import UserUpdateRole

    with pytest.raises(AdminUserError, match="only remaining admin"):
        await user_service.update_role(
            database.admin_id,
            UserUpdateRole(role=UserRole.operator),
            database.admin_id,
        )


async def test_update_role_can_demote_operator_as_admin(
    user_service: UserService, database: Database
) -> None:
    from app.schemas.admin import UserUpdateRole

    updated = await user_service.update_role(
        database.operator_id,
        UserUpdateRole(role=UserRole.admin),
        database.admin_id,
    )
    assert updated.role == UserRole.admin


async def test_deactivate_self_blocked(
    user_service: UserService, database: Database
) -> None:
    with pytest.raises(AdminUserError, match="own account"):
        await user_service.deactivate_user(database.admin_id, database.admin_id)


async def test_get_user_returns_none_for_unknown_id(
    user_service: UserService,
) -> None:
    result = await user_service.get_user(uuid4())
    assert result is None


async def test_deactivate_user_marks_inactive(
    user_service: UserService, database: Database
) -> None:
    await user_service.deactivate_user(database.operator_id, database.admin_id)
    user = await user_service.get_user(database.operator_id)
    assert user is not None
    assert user.deactivated is True
