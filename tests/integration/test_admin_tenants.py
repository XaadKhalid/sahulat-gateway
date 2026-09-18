import pytest

from app.core.admin_config import AdminSettings
from app.schemas.admin import DocumentStatus, TenantStatus
from app.services.tenant_service import TenantService
from tests.integration.conftest import Database


@pytest.fixture
def admin_settings() -> AdminSettings:
    return AdminSettings()


@pytest.fixture
def tenant_service(database: Database) -> TenantService:
    return TenantService(database.sessions)


# ---------------------------------------------------------------------------
# Tenant listing & detail
# ---------------------------------------------------------------------------


async def test_list_tenants_returns_seeded_tenants(
    tenant_service: TenantService, database: Database
) -> None:
    items, next_cursor = await tenant_service.list_tenants(50, None)
    assert len(items) == 2
    names = {t.name for t in items}
    assert "Retailer A" in names
    assert "Retailer B" in names
    assert all(t.status == TenantStatus.draft for t in items)
    assert next_cursor is None


async def test_list_tenants_with_limit_returns_cursor(
    tenant_service: TenantService,
) -> None:
    items, next_cursor = await tenant_service.list_tenants(1, None)
    assert len(items) == 1
    assert next_cursor is not None


async def test_get_tenant_detail_returns_document_count(
    tenant_service: TenantService, database: Database
) -> None:
    tenant = await tenant_service.get_tenant(database.tenant_a)
    assert tenant is not None
    assert tenant.id == database.tenant_a
    assert tenant.name == "Retailer A"
    assert tenant.document_count == 0
    assert tenant.manifest_status is not None  # ManifestStatus enum
    assert tenant.status == TenantStatus.draft
    assert tenant.whatsapp_connected is False


async def test_get_tenant_detail_for_unknown_id_returns_none(
    tenant_service: TenantService,
) -> None:
    from uuid import uuid4

    result = await tenant_service.get_tenant(uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# Tenant creation & update
# ---------------------------------------------------------------------------


async def test_create_tenant_adds_to_list(
    tenant_service: TenantService,
) -> None:
    from app.schemas.admin import TenantCreate

    detail = await tenant_service.create_tenant(TenantCreate(name="New Co"))
    assert detail.name == "New Co"
    assert detail.status == TenantStatus.draft
    assert detail.whatsapp_connected is False
    assert detail.document_count == 0
    assert detail.manifest_status.value == "pending"


async def test_update_tenant_name(
    tenant_service: TenantService, database: Database
) -> None:
    from app.schemas.admin import TenantUpdate

    updated = await tenant_service.update_tenant(
        database.tenant_a, TenantUpdate(name="Updated Retailer A", policy=None)
    )
    assert updated is not None
    assert updated.name == "Updated Retailer A"


async def test_update_tenant_policy_merges(
    tenant_service: TenantService, database: Database
) -> None:
    from app.schemas.admin import TenantUpdate

    updated = await tenant_service.update_tenant(
        database.tenant_a,
        TenantUpdate(
            name=None,
            policy={"languages": "en,es"},
        ),
    )
    assert updated is not None
    policy_dict = updated.policy.model_dump()
    assert policy_dict["languages"] == "en,es"
    assert policy_dict["persona"] == "You are a helpful business assistant."


# ---------------------------------------------------------------------------
# Document management
# ---------------------------------------------------------------------------


async def test_upload_and_list_document(
    tenant_service: TenantService, database: Database
) -> None:
    doc = await tenant_service.upload_document(
        database.tenant_a, "invoice.pdf", "application/pdf", 4096
    )
    assert doc.filename == "invoice.pdf"
    assert doc.mime_type == "application/pdf"
    assert doc.status == DocumentStatus.processing

    listing = await tenant_service.list_documents(database.tenant_a, 50, None)
    assert len(listing.items) == 1
    assert listing.items[0].filename == "invoice.pdf"
    assert listing.items[0].status == DocumentStatus.processing


async def test_delete_document(
    tenant_service: TenantService, database: Database
) -> None:
    doc = await tenant_service.upload_document(
        database.tenant_a, "contract.pdf", "application/pdf", 8192
    )
    deleted = await tenant_service.delete_document(database.tenant_a, doc.document_id)
    assert deleted is True

    listing = await tenant_service.list_documents(database.tenant_a, 50, None)
    assert len(listing.items) == 0


async def test_delete_unknown_document_returns_false(
    tenant_service: TenantService, database: Database
) -> None:
    from uuid import uuid4

    result = await tenant_service.delete_document(database.tenant_a, uuid4())
    assert result is False
