from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.health import create_health_router
from app.api.limits import GatewayRequestLimits
from app.api.webhooks import create_webhooks_router
from app.core.config import DatabaseSettings, Settings
from app.infrastructure.database import create_database_engine
from app.services.ingress import IngressService


def create_app() -> FastAPI:
    settings = Settings()
    db_settings = DatabaseSettings()
    engine = create_database_engine(db_settings)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    ingress_service = IngressService(sessions)

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
    application.include_router(create_health_router())
    application.include_router(create_webhooks_router(settings, ingress_service))
    return application
