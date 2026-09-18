from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.health import create_health_router
from app.api.limits import GatewayRequestLimits
from app.api.v1 import create_v1_router
from app.api.webhooks import create_webhooks_router
from app.core.admin_config import AdminSettings
from app.core.config import DatabaseSettings, Settings
from app.infrastructure.database import create_database_engine
from app.services.auth_service import AuthService
from app.services.ingress import IngressService
from app.services.tenant_service import TenantService
from app.services.user_service import UserService


def create_app() -> FastAPI:
    settings = Settings()
    db_settings = DatabaseSettings()
    admin_settings = AdminSettings()
    engine = create_database_engine(db_settings)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    ingress_service = IngressService(sessions)
    auth_service = AuthService(sessions, admin_settings)
    user_service = UserService(sessions)
    tenant_service = TenantService(sessions)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield
        await engine.dispose()

    application = FastAPI(
        title="Sahulat Gateway",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    limits = GatewayRequestLimits(
        health_limit=settings.health_requests_per_second,
        webhook_limit=settings.webhook_requests_per_second,
    )
    application.middleware("http")(limits.dispatch)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8080", "http://0.0.0.0:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(create_health_router())
    application.include_router(create_webhooks_router(settings, ingress_service))
    application.include_router(
        create_v1_router(
            auth_service,
            user_service,
            tenant_service,
            admin_settings,
        )
    )
    return application


app = create_app()
