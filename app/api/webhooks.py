import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request, Response

from app.core.config import Settings
from app.schemas.whatsapp import WhatsAppWebhook
from app.services.ingress import IngressService


def create_webhooks_router(
    settings: Settings, ingress_service: IngressService
) -> APIRouter:
    router = APIRouter(prefix="/webhooks/whatsapp")

    @router.get("")
    async def verify_webhook(
        request: Request,
    ) -> Response:
        mode = request.query_params.get("hub.mode")
        verify_token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if (
            mode == "subscribe"
            and verify_token == settings.webhook_verify_token.get_secret_value()
        ):
            return Response(content=challenge, media_type="text/plain")

        raise HTTPException(status_code=403, detail="Invalid verify token")

    @router.post("/{route_key}")
    async def receive_webhook(
        route_key: str,
        request: Request,
    ) -> Response:
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256")

        if not signature or not signature.startswith("sha256="):
            raise HTTPException(
                status_code=401, detail="Missing or invalid signature format"
            )

        expected_mac = hmac.new(
            settings.webhook_secret.get_secret_value().encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(f"sha256={expected_mac}", signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

        try:
            payload = WhatsAppWebhook.model_validate_json(body)
        except Exception as e:
            raise HTTPException(status_code=422, detail="Invalid payload") from e

        await ingress_service.process_webhook(route_key, payload)
        return Response(status_code=200)

    return router
