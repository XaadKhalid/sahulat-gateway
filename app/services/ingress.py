from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database import tenant_transaction
from app.repositories.audit import AuditRepository
from app.repositories.dispatch import DispatchRepository
from app.repositories.messages import MessageRepository
from app.repositories.sessions import SessionRepository
from app.repositories.tenants import TenantRepository
from app.schemas.audit import AuditEvent
from app.schemas.messages import MessageEnvelope, TextContent
from app.schemas.sessions import SessionIdentity
from app.schemas.tenants import RouteLookup
from app.schemas.whatsapp import WhatsAppWebhook


class IngressService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def process_webhook(self, route_key: str, payload: WhatsAppWebhook) -> None:
        async with self._sessions() as global_session:
            tenant_repo = TenantRepository(global_session)
            tenant_route = await tenant_repo.resolve(RouteLookup(route_key=route_key))
            if tenant_route is None:
                raise HTTPException(status_code=404, detail="Route not found")

        tenant_id = tenant_route.tenant_id

        for entry in payload.entry:
            for change in entry.changes:
                messages = change.value.messages
                if not messages:
                    continue

                for msg in messages:
                    if msg.type != "text" or msg.text is None:
                        continue  # Ignore status/unsupported

                    async with tenant_transaction(self._sessions, tenant_id) as session:
                        session_repo = SessionRepository(session)
                        conversation = await session_repo.get_or_create(
                            SessionIdentity(
                                tenant_id=tenant_id, customer_number=msg.from_
                            )
                        )

                        msg_repo = MessageRepository(session)
                        envelope = MessageEnvelope(
                            id=uuid4(),
                            tenant_id=tenant_id,
                            session_id=conversation.id,
                            channel="whatsapp",
                            provider_message_id=msg.id,
                            content=TextContent(text=msg.text.body),
                            occurred_at=datetime.fromtimestamp(
                                int(msg.timestamp), tz=UTC
                            ),
                        )
                        save_result = await msg_repo.save(envelope)

                        if save_result.created:
                            audit_repo = AuditRepository(session)
                            await audit_repo.append(
                                AuditEvent(
                                    tenant_id=tenant_id,
                                    id=uuid4(),
                                    occurred_at=datetime.now(UTC),
                                    event_type="message.received",
                                    actor="customer",
                                    details={"channel": "whatsapp"},
                                )
                            )

                            dispatch_repo = DispatchRepository(session)
                            await dispatch_repo.enqueue(
                                tenant_id, save_result.message.id
                            )
