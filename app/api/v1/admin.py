from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)

from app.core.admin_config import AdminSettings
from app.schemas.admin import (
    DocumentList,
    DocumentRead,
    LoginRequest,
    MeResponse,
    TenantCreate,
    TenantDetail,
    TenantUpdate,
    UserCreate,
    UserRead,
    UserRole,
    UserUpdateRole,
)
from app.services.auth_service import AuthService
from app.services.tenant_service import TenantService
from app.services.user_service import UserService


def _forbidden(detail: str, err_type: str, code: int) -> HTTPException:
    return HTTPException(
        status_code=code,
        detail={"detail": detail, "type": err_type},
    )


def create_admin_router(
    auth_service: AuthService,
    user_service: UserService,
    tenant_service: TenantService,
    admin_settings: AdminSettings,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
    cookie_name = admin_settings.admin_session_cookie
    ttl_seconds = admin_settings.admin_session_ttl_seconds

    async def require_user(request: Request) -> MeResponse:
        raw = request.cookies.get(cookie_name)
        if raw is None:
            raise _forbidden(
                "Authentication required.",
                "auth_required",
                status.HTTP_401_UNAUTHORIZED,
            )
        try:
            session_id = UUID(raw)
        except ValueError:
            raise _forbidden(
                "Authentication required.",
                "auth_required",
                status.HTTP_401_UNAUTHORIZED,
            ) from None
        user = await auth_service.get_current(session_id)
        if user is None:
            raise _forbidden(
                "Authentication required.",
                "auth_required",
                status.HTTP_401_UNAUTHORIZED,
            )
        return user

    async def require_admin(request: Request) -> MeResponse:
        user = await require_user(request)
        if user.role != UserRole.admin:
            raise _forbidden(
                "Insufficient role for this operation.",
                "forbidden",
                status.HTTP_403_FORBIDDEN,
            )
        return user

    @router.post("/auth/login")
    async def login(
        response: Response,
        payload: LoginRequest,
    ) -> MeResponse:
        result = await auth_service.login(payload.email, payload.password)
        if result is None:
            raise _forbidden(
                "Invalid email or password.",
                "invalid_credentials",
                status.HTTP_401_UNAUTHORIZED,
            )
        me, session_id = result
        response.set_cookie(
            cookie_name,
            session_id,
            httponly=True,
            samesite="lax",
            max_age=ttl_seconds,
            secure=False,
            path="/",
        )
        return me

    @router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    async def logout(request: Request, response: Response) -> None:
        raw = request.cookies.get(cookie_name)
        if raw is not None:
            try:
                session_id = UUID(raw)
                await auth_service.logout(session_id)
            except ValueError:
                pass
        response.delete_cookie(cookie_name, path="/")

    @router.get("/auth/me")
    async def me(
        current: MeResponse = Depends(require_user),
    ) -> MeResponse:
        return current

    @router.get("/users")
    async def list_users(
        limit: int = 50,
        cursor: str | None = None,
        _auth: MeResponse = Depends(require_user),
    ) -> dict[str, object]:
        try:
            cursor_uuid = UUID(cursor) if cursor else None
        except ValueError:
            raise _forbidden(
                "Invalid cursor.",
                "invalid_cursor",
                status.HTTP_400_BAD_REQUEST,
            ) from None
        items, next_cursor = await user_service.list_users(min(limit, 100), cursor_uuid)
        return {
            "items": [item.model_dump() for item in items],
            "next_cursor": next_cursor,
        }

    @router.post("/users", status_code=status.HTTP_201_CREATED)
    async def create_user(
        payload: UserCreate,
        _auth: MeResponse = Depends(require_admin),
    ) -> UserRead:
        from app.services.user_service import AdminUserError

        try:
            return await user_service.create_user(payload)
        except AdminUserError:
            raise _forbidden(
                "A user with this email already exists.",
                "user_exists",
                status.HTTP_409_CONFLICT,
            ) from None

    @router.patch("/users/{user_id}")
    async def update_user_role(
        user_id: UUID,
        payload: UserUpdateRole,
        _auth: MeResponse = Depends(require_admin),
    ) -> UserRead:
        from app.services.user_service import AdminUserError

        try:
            return await user_service.update_role(user_id, payload, _auth.id)
        except AdminUserError as exc:
            msg = str(exc)
            if "only" in msg.lower():
                raise _forbidden(
                    msg,
                    "cannot_demote_last_admin",
                    status.HTTP_409_CONFLICT,
                ) from None
            raise _forbidden(
                msg,
                "user_not_found",
                status.HTTP_404_NOT_FOUND,
            ) from None

    @router.delete(
        "/users/{user_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_user(
        user_id: UUID,
        _auth: MeResponse = Depends(require_admin),
    ) -> Response:
        from app.services.user_service import AdminUserError

        try:
            await user_service.deactivate_user(user_id, _auth.id)
        except AdminUserError as exc:
            msg = str(exc)
            if "own account" in msg.lower():
                raise _forbidden(
                    msg,
                    "cannot_deactivate_self",
                    status.HTTP_409_CONFLICT,
                ) from None
            if "last" in msg.lower():
                raise _forbidden(
                    msg,
                    "cannot_deactivate_last_admin",
                    status.HTTP_409_CONFLICT,
                ) from None
            raise _forbidden(
                msg,
                "user_not_found",
                status.HTTP_404_NOT_FOUND,
            ) from None
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/tenants")
    async def list_tenants(
        limit: int = 50,
        cursor: str | None = None,
        _auth: MeResponse = Depends(require_user),
    ) -> dict[str, object]:
        from uuid import UUID as _UUID

        try:
            cursor_uuid = _UUID(cursor) if cursor else None
        except ValueError:
            raise _forbidden(
                "Invalid cursor.",
                "invalid_cursor",
                status.HTTP_400_BAD_REQUEST,
            ) from None
        items, next_cursor = await tenant_service.list_tenants(
            min(limit, 100), cursor_uuid
        )
        return {
            "items": [item.model_dump(mode="json") for item in items],
            "next_cursor": next_cursor,
        }

    @router.get("/tenants/{tenant_id}")
    async def get_tenant(
        tenant_id: UUID,
        _auth: MeResponse = Depends(require_user),
    ) -> TenantDetail:
        tenant = await tenant_service.get_tenant(tenant_id)
        if tenant is None:
            raise _forbidden(
                "Tenant not found.",
                "tenant_not_found",
                status.HTTP_404_NOT_FOUND,
            )
        return tenant

    @router.post("/tenants", status_code=status.HTTP_201_CREATED)
    async def create_tenant(
        payload: TenantCreate,
        _auth: MeResponse = Depends(require_admin),
    ) -> TenantDetail:
        return await tenant_service.create_tenant(payload)

    @router.patch("/tenants/{tenant_id}")
    async def update_tenant(
        tenant_id: UUID,
        payload: TenantUpdate,
        _auth: MeResponse = Depends(require_admin),
    ) -> TenantDetail:
        updated = await tenant_service.update_tenant(tenant_id, payload)
        if updated is None:
            raise _forbidden(
                "Tenant not found.",
                "tenant_not_found",
                status.HTTP_404_NOT_FOUND,
            )
        return updated

    @router.get("/tenants/{tenant_id}/documents")
    async def list_documents(
        tenant_id: UUID,
        limit: int = 50,
        cursor: str | None = None,
        _auth: MeResponse = Depends(require_user),
    ) -> DocumentList:
        from uuid import UUID as _UUID

        try:
            cursor_uuid = _UUID(cursor) if cursor else None
        except ValueError:
            raise _forbidden(
                "Invalid cursor.",
                "invalid_cursor",
                status.HTTP_400_BAD_REQUEST,
            ) from None
        result = await tenant_service.list_documents(
            tenant_id, min(limit, 100), cursor_uuid
        )
        return result

    @router.post(
        "/tenants/{tenant_id}/documents",
        status_code=status.HTTP_201_CREATED,
    )
    async def upload_document(
        tenant_id: UUID,
        filename: str,
        mime_type: str,
        size_bytes: int,
        _auth: MeResponse = Depends(require_admin),
    ) -> DocumentRead:
        return await tenant_service.upload_document(
            tenant_id, filename, mime_type, size_bytes
        )

    @router.delete(
        "/tenants/{tenant_id}/documents/{document_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_document(
        tenant_id: UUID,
        document_id: UUID,
        _auth: MeResponse = Depends(require_admin),
    ) -> Response:
        deleted = await tenant_service.delete_document(tenant_id, document_id)
        if not deleted:
            raise _forbidden(
                "Document not found.",
                "document_not_found",
                status.HTTP_404_NOT_FOUND,
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
