from fastapi import APIRouter

from app.schemas.health import HealthResponse


async def check_health() -> HealthResponse:
    """Public process liveness only; no tenant or dependency information."""
    return HealthResponse()


def create_health_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/health", check_health, methods=["GET"])
    return router
