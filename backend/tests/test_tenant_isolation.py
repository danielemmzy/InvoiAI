"""Ticket 4 — cross-tenant isolation at the API and worker boundary.

RLS is enforced in Postgres by
`migrations/20261012_tenant_isolation_rls_and_audit_indexes.sql`. These tests
prove the application layer never relies on RLS alone: every query scopes by
the authenticated organization, and a cross-tenant detail request returns a
safe 404 instead of leaking record existence.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.context import AuthUser, OrganizationContext
from app.core.auth import get_current_user
from app.core.enum.database import OrgRole, PlanType
from app.core.ocm import get_org_context
from app.core.permissions import MANAGE_FINANCE, VIEW_DOCUMENTS, VIEW_FINANCE


ORG_A = UUID("00000000-0000-0000-0000-0000000000a1")
ORG_B = UUID("00000000-0000-0000-0000-0000000000b2")
USER_A = UUID("00000000-0000-0000-0000-0000000000c3")


def make_context(org_id: UUID) -> OrganizationContext:
    return OrganizationContext(
        user_id=str(USER_A),
        org_id=org_id,
        name="Org",
        slug=f"org-{str(org_id)[-2:]}",
        plan=PlanType.FREE,
        role=OrgRole.OWNER,
        permissions={VIEW_DOCUMENTS, VIEW_FINANCE, MANAGE_FINANCE},
        document_limit=100,
        default_currency="GBP",
        timezone="Europe/London",
    )


@pytest.fixture
def tenant_client(fake_db, monkeypatch):
    from app.main import app
    import app.routers.ap as ap_router

    monkeypatch.setattr(ap_router, "db", lambda: fake_db)

    user = AuthUser(
        id=USER_A,
        email="isolation@example.com",
        org_id=ORG_A,
        role=OrgRole.OWNER,
    )

    previous = dict(app.dependency_overrides)

    def as_org(org_id: UUID):
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_org_context] = lambda: make_context(org_id)

    as_org(ORG_A)

    try:
        with TestClient(app) as client:
            client.as_org = as_org  # type: ignore[attr-defined]
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def seed_document(fake_db, *, org_id: UUID, document_id: UUID, **extra):
    fake_db.seed(
        "documents",
        {
            "id": str(document_id),
            "org_id": str(org_id),
            "document_type": "invoice",
            "ap_enabled": True,
            "ap_status": "approved",
            "document_number": "INV-1",
            "total_amount": 100,
            "currency": "GBP",
            "updated_at": "2026-11-09T00:00:00Z",
            **extra,
        },
    )


def test_status_detail_is_denied_across_tenants(tenant_client, fake_db):
    document_id = uuid4()
    seed_document(fake_db, org_id=ORG_A, document_id=document_id)

    tenant_client.as_org(ORG_A)
    own = tenant_client.get(f"/api/v2/ap/documents/{document_id}/status")
    assert own.status_code == 200

    tenant_client.as_org(ORG_B)
    other = tenant_client.get(f"/api/v2/ap/documents/{document_id}/status")
    assert other.status_code == 404
    # A safe denial must not disclose whether some other tenant owns the id.
    assert "Document not found" in other.text
    assert str(document_id) not in other.text


def test_codings_list_does_not_leak_across_tenants(tenant_client, fake_db):
    document_id = uuid4()
    seed_document(fake_db, org_id=ORG_A, document_id=document_id)
    fake_db.seed(
        "invoice_codings",
        {
            "id": str(uuid4()),
            "org_id": str(ORG_A),
            "document_id": str(document_id),
            "status": "approved",
            "created_at": "2026-11-09T00:00:00Z",
        },
    )

    tenant_client.as_org(ORG_A)
    own = tenant_client.get(f"/api/v2/ap/codings/{document_id}")
    assert own.status_code == 200
    assert len(own.json()) == 1

    tenant_client.as_org(ORG_B)
    other = tenant_client.get(f"/api/v2/ap/codings/{document_id}")
    assert other.status_code == 200
    assert other.json() == []


async def test_worker_derives_organization_from_record_not_job(monkeypatch):
    """The worker accepts only a document id; org comes from the stored row."""
    from tests.conftest import FakeDatabase
    import app.workers.bill_sync_worker as worker_module

    database = FakeDatabase()
    document_id = uuid4()
    document_org = uuid4()
    database.seed(
        "documents",
        {
            "id": str(document_id),
            "org_id": str(document_org),
            "ap_enabled": True,
            "ap_status": "approved",
            "erp_bill_id": None,
        },
    )

    seen_orgs: list[UUID] = []

    class Provider:
        async def create_bill(self, *, org_id, document_id):
            seen_orgs.append(org_id)
            database.table("documents").update(
                {"erp_bill_id": "ERP-1", "ap_status": "payment_ready"}
            ).eq("id", str(document_id)).execute()
            return "ERP-1"

    async def fake_provider(org_id, _db=None):
        return Provider()

    class FakePaymentAuthorizationService:
        def __init__(self, db):
            self.db = db

        async def evaluate(self, **_kwargs):
            return None

    monkeypatch.setattr(worker_module, "get_accounting_provider", fake_provider)
    monkeypatch.setattr(worker_module, "PaymentAuthorizationService", FakePaymentAuthorizationService)

    result = await worker_module.BillSyncWorker(db=database).run(document_id=document_id)

    assert result["status"] == "payment_ready"
    assert seen_orgs == [document_org]


async def test_matching_worker_does_not_process_foreign_tenant_line_items(monkeypatch):
    """Mis-scoped child rows must not enter another tenant's matching run."""
    from tests.conftest import FakeDatabase
    from app.core.enum.ap import APMatchStatus, InvoiceAPStatus
    import app.workers.ap_matching_worker as worker_module

    database = FakeDatabase()
    document_id = uuid4()
    document_org = uuid4()
    other_org = uuid4()
    foreign_line = {
        "id": str(uuid4()),
        "org_id": str(other_org),
        "document_id": str(document_id),
    }
    database.seed(
        "documents",
        {
            "id": str(document_id),
            "org_id": str(document_org),
            "document_type": "invoice",
            "ap_enabled": True,
            "ap_status": InvoiceAPStatus.MATCHING.value,
        },
    )
    database.seed("document_line_items", foreign_line)

    seen_lines = []

    class FakeState:
        async def transition(self, *_args, **_kwargs):
            return None

    class FakeMatchingService:
        def __init__(self, _db):
            pass

        async def run(self, **kwargs):
            seen_lines.extend(kwargs["line_items"])
            return SimpleNamespace(status=APMatchStatus.EXCEPTION, exceptions=[object()])

    monkeypatch.setattr(worker_module, "InvoiceStateMachine", lambda _db: FakeState())
    monkeypatch.setattr(worker_module, "MatchingService", FakeMatchingService)

    await worker_module.APMatchingWorker(db=database)._run_once(document_id=document_id)

    assert seen_lines == []


def test_export_denies_foreign_document_before_exporting(tenant_client, monkeypatch):
    import app.routers.export_v2 as export_router

    document_id = uuid4()
    exported = []

    class DocumentService:
        async def get_document(self, _document_id):
            return SimpleNamespace(org_id=ORG_A)

    class ExportService:
        async def export(self, **kwargs):
            exported.append(kwargs)

    monkeypatch.setattr(
        export_router,
        "get_container",
        lambda: SimpleNamespace(
            document_service=DocumentService(), export_service=ExportService()
        ),
    )
    tenant_client.as_org(ORG_B)

    response = tenant_client.get(f"/api/v2/export/{document_id}/csv")

    assert response.status_code == 404
    assert "Document not found" in response.text
    assert str(document_id) not in response.text
    assert exported == []


def test_document_detail_denies_foreign_tenant(tenant_client, monkeypatch):
    import app.routers.documents as documents_router

    document_id = uuid4()

    class DocumentService:
        async def get_document(self, _document_id):
            return SimpleNamespace(org_id=ORG_A)

    monkeypatch.setattr(
        documents_router,
        "get_container",
        lambda: SimpleNamespace(document_service=DocumentService()),
    )
    tenant_client.as_org(ORG_B)

    response = tenant_client.get(f"/api/v2/documents/{document_id}")

    assert response.status_code == 404
    assert "Document not found" in response.text
    assert str(document_id) not in response.text


def test_foreign_document_does_not_create_a_signed_download(
    tenant_client, fake_db, monkeypatch
):
    import app.routers.documents as documents_router

    document_id = uuid4()
    seed_document(
        fake_db,
        org_id=ORG_A,
        document_id=document_id,
        file_url="private/org-a/invoice.pdf",
        file_name="invoice.pdf",
        file_type="application/pdf",
        status="complete",
        processing_step="complete",
        intelligence_status="complete",
    )
    signed = []

    class StorageService:
        async def create_signed_url(self, *, path, expires_in):
            signed.append((path, expires_in))
            return "https://storage.invalid/signed"

    monkeypatch.setattr(documents_router, "get_supabase", lambda: fake_db)
    monkeypatch.setattr(
        documents_router,
        "get_container",
        lambda: SimpleNamespace(storage_service=StorageService()),
    )
    tenant_client.as_org(ORG_B)

    response = tenant_client.get(f"/api/v2/documents/{document_id}/intelligence")

    assert response.status_code == 404
    assert "Document not found" in response.text
    assert signed == []
