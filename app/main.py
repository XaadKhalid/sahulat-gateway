from fastapi import FastAPI

from app.api.health import create_health_router
from app.api.limits import HealthRequestLimits
from app.core.config import Settings


def create_app() -> FastAPI:
    settings = Settings()
    application = FastAPI(
        title="Sahulat Gateway",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    limits = HealthRequestLimits(settings.health_requests_per_second)
    application.middleware("http")(limits.dispatch)
    application.include_router(create_health_router())
    return application
