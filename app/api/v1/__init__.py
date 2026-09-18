from fastapi import APIRouter

from app.api.v1.admin import create_admin_router
from app.core.admin_config import AdminSettings
from app.services.auth_service import AuthService
from app.services.tenant_service import TenantService
from app.services.user_service import UserService


def create_v1_router(
    auth_service: AuthService,
    user_service: UserService,
    tenant_service: TenantService,
    admin_settings: AdminSettings,
) -> APIRouter:
    router = APIRouter()
    router.include_router(
        create_admin_router(
            auth_service,
            user_service,
            tenant_service,
            admin_settings,
        )
    )
    return router
