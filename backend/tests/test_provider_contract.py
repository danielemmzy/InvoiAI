"""Ticket 2 — provider-contract suite.

Runs the same behavioural assertions against every required accounting
provider using a fake HTTP transport at the client boundary. Nothing in the
service/worker layer is mocked except the provider selection seam.
"""

from __future__ import annotations

import base64
from uuid import UUID, uuid4

import httpx
import pytest

from app.core.config import settings
from app.integrations.quickbooks.client import QuickBooksClient
from app.integrations.xero.client import XeroClient
from app.services.ap.provider.contracts import (
    PROVIDER_CONTRACTS,
    SAGE,
    UnsupportedProviderOperationError,
    ensure_purchase_orders_supported,
)
from app.services.ap.provider.sage_boundary import (
    SageUnsupportedResourceError,
    assert_sage_allowed,
)
from tests.provider_contract_support import FakeTokens, FakeTransport, SleepRecorder, json_response


ORG_ID = UUID("00000000-0000-0000-0000-0000000000aa")
REALM_ID = "realm-913"
TENANT_ID = "tenant-913"


@pytest.fixture(autouse=True)
def _token_key(monkeypatch):
    key = base64.urlsafe_b64encode(b"\x00" * 32).decode("ascii")
    monkeypatch.setattr(settings, "token_encryption_key", key)


def build_client(provider: str, transport: FakeTransport, sleep: SleepRecorder):
    if provider == "quickbooks":
        client = QuickBooksClient(
            org_id=ORG_ID,
            realm_id=REALM_ID,
            transport=transport.transport,
            sleep=sleep,
        )
        client.tokens = FakeTokens()
        return client, "/bill"

    if provider == "xero":
        client = XeroClient(
            org_id=ORG_ID,
            transport=transport.transport,
            sleep=sleep,
        )
        client.tokens = FakeTokens(tenant_id=TENANT_ID)
        return client, "/Invoices"

    raise AssertionError(f"No contract client for {provider}")


# ---------------------------------------------------------------------------
# Harness registration and provider metadata
# ---------------------------------------------------------------------------


def test_contract_harness_registers_every_required_provider():
    assert set(PROVIDER_CONTRACTS) == {"quickbooks", "xero", "sage"}


def test_sage_metadata_uses_trial_business_and_verified_business_header():
    assert SAGE.evidence_environment == "trial business"
    assert "sandbox" not in SAGE.evidence_environment
    assert SAGE.organization_header == "X-Business"
    assert SAGE.supports_purchase_orders is False


async def test_organization_headers_or_urls_match_each_provider():
    quickbooks, _ = build_client("quickbooks", FakeTransport(), SleepRecorder())
    assert quickbooks.base_url.endswith(f"/v3/company/{REALM_ID}")

    xero, _ = build_client("xero", FakeTransport(), SleepRecorder())
    assert (await xero.headers())["Xero-tenant-id"] == TENANT_ID

    assert SAGE.organization_header == "X-Business"


# ---------------------------------------------------------------------------
# Shared transport behaviour
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider", ["quickbooks", "xero"])
async def test_exactly_one_create_request_on_first_success(provider):
    transport = FakeTransport([json_response(200, {"ok": True})])
    client, endpoint = build_client(provider, transport, SleepRecorder())

    await client.post(endpoint, json={"Amount": 10})

    assert transport.calls == 1
    assert [r.method for r in transport.requests] == ["POST"]


@pytest.mark.parametrize("provider", ["quickbooks", "xero"])
async def test_retries_after_5xx_then_succeeds(provider):
    transport = FakeTransport(
        [json_response(503), json_response(502), json_response(200, {"ok": True})]
    )
    sleep = SleepRecorder()
    client, endpoint = build_client(provider, transport, sleep)

    result = await client.post(endpoint, json={"Amount": 10})

    assert result == {"ok": True}
    assert transport.calls == 3
    assert sleep.delays == [2, 4]


@pytest.mark.parametrize("provider", ["quickbooks", "xero"])
async def test_stops_immediately_after_4xx(provider):
    transport = FakeTransport([json_response(400, {"error": "bad"})])
    sleep = SleepRecorder()
    client, endpoint = build_client(provider, transport, sleep)

    with pytest.raises(Exception) as excinfo:
        await client.post(endpoint, json={"Amount": 10})

    assert getattr(excinfo.value, "status_code", None) == 400
    assert transport.calls == 1
    assert sleep.delays == []


@pytest.mark.parametrize("provider", ["quickbooks", "xero"])
async def test_backs_off_using_retry_after_on_429(provider):
    transport = FakeTransport(
        [json_response(429, headers={"Retry-After": "7"}), json_response(200, {"ok": True})]
    )
    sleep = SleepRecorder()
    client, endpoint = build_client(provider, transport, sleep)

    result = await client.post(endpoint, json={"Amount": 10})

    assert result == {"ok": True}
    assert transport.calls == 2
    assert sleep.delays == [7.0]


@pytest.mark.parametrize("provider", ["quickbooks", "xero"])
async def test_timeout_retries_before_succeeding(provider):
    transport = FakeTransport(
        [httpx.ConnectTimeout("timed out"), json_response(200, {"ok": True})]
    )
    sleep = SleepRecorder()
    client, endpoint = build_client(provider, transport, sleep)

    result = await client.post(endpoint, json={"Amount": 10})

    assert result == {"ok": True}
    assert transport.calls == 2
    assert sleep.delays == [2]


# ---------------------------------------------------------------------------
# Capability and boundary assertions
# ---------------------------------------------------------------------------


def test_provider_without_po_support_fails_with_typed_error():
    with pytest.raises(UnsupportedProviderOperationError):
        ensure_purchase_orders_supported("sage")

    ensure_purchase_orders_supported("quickbooks")
    ensure_purchase_orders_supported("xero")


@pytest.mark.parametrize(
    "path",
    [
        "/bank_accounts",
        "/bank_transactions",
        "/journals",
        "/payments",
        "/receipts",
        "/sales_invoices",
        "/sales_credit_notes",
        "/opening_balances",
        "/products",
        "/services",
        "/reports/profit_and_loss",
    ],
)
def test_sage_never_allows_excluded_resources(path):
    with pytest.raises(SageUnsupportedResourceError):
        assert_sage_allowed("GET", path)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/businesses"),
        ("GET", "/contacts"),
        ("GET", "/ledger_accounts"),
        ("GET", "/purchase_invoices"),
        ("GET", "/status_codes"),
        ("GET", "/currencies"),
        ("GET", "/tax_rates"),
        ("GET", "/settings"),
        ("POST", "/purchase_invoices"),
        ("PUT", "/purchase_credit_notes/123"),
    ],
)
def test_sage_allows_only_agreed_ap_resources(method, path):
    assert_sage_allowed(method, path)


def test_sage_refuses_writes_outside_purchase_transactions_and_all_deletes():
    with pytest.raises(SageUnsupportedResourceError):
        assert_sage_allowed("POST", "/contacts")

    with pytest.raises(SageUnsupportedResourceError):
        assert_sage_allowed("DELETE", "/purchase_invoices/123")


# ---------------------------------------------------------------------------
# Worker contract: no pre-approval call, one call, timeout adoption
# ---------------------------------------------------------------------------


class FakeProvider:
    def __init__(self, db, *, persist: bool, error: Exception | None = None):
        self.db = db
        self.persist = persist
        self.error = error
        self.calls = 0

    async def create_bill(self, *, org_id, document_id):
        self.calls += 1
        if self.persist:
            self.db.table("documents").update(
                {"erp_bill_id": "ERP-BILL-1", "ap_status": "payment_ready"}
            ).eq("id", str(document_id)).execute()
        if self.error:
            raise self.error
        return "ERP-BILL-1"


@pytest.fixture
def worker_env(fake_db, monkeypatch):
    import app.workers.bill_sync_worker as worker_module

    class FakePaymentAuthorizationService:
        def __init__(self, db):
            self.db = db

        async def evaluate(self, **_kwargs):
            return None

    monkeypatch.setattr(worker_module, "PaymentAuthorizationService", FakePaymentAuthorizationService)
    return worker_module


def seed_document(fake_db, *, status: str):
    document_id = uuid4()
    org_id = uuid4()
    fake_db.seed(
        "documents",
        {
            "id": str(document_id),
            "org_id": str(org_id),
            "ap_enabled": True,
            "ap_status": status,
            "erp_bill_id": None,
            "document_type": "invoice",
        },
    )
    return document_id, org_id


async def test_worker_makes_no_provider_call_before_approval(worker_env, fake_db, monkeypatch):
    document_id, _ = seed_document(fake_db, status="awaiting_approval")
    provider = FakeProvider(fake_db, persist=True)

    async def fake_provider(_org_id, _db=None):
        return provider

    monkeypatch.setattr(worker_env, "get_accounting_provider", fake_provider)

    result = await worker_env.BillSyncWorker(db=fake_db).run(document_id=document_id)

    assert result == {"status": "not_eligible"}
    assert provider.calls == 0


async def test_worker_creates_once_on_first_attempt(worker_env, fake_db, monkeypatch):
    document_id, _ = seed_document(fake_db, status="approved")
    provider = FakeProvider(fake_db, persist=True)

    async def fake_provider(_org_id, _db=None):
        return provider

    monkeypatch.setattr(worker_env, "get_accounting_provider", fake_provider)

    result = await worker_env.BillSyncWorker(db=fake_db).run(document_id=document_id)

    assert result["status"] == "payment_ready"
    assert provider.calls == 1

    row = fake_db.table("documents").select("*").eq("id", str(document_id)).single().execute().data
    assert row["erp_bill_id"] == "ERP-BILL-1"


async def test_worker_adopts_persisted_bill_after_timeout(worker_env, fake_db, monkeypatch):
    document_id, _ = seed_document(fake_db, status="approved")
    provider = FakeProvider(
        fake_db,
        persist=True,
        error=httpx.TimeoutException("provider timed out after accepting the bill"),
    )

    async def fake_provider(_org_id, _db=None):
        return provider

    monkeypatch.setattr(worker_env, "get_accounting_provider", fake_provider)

    result = await worker_env.BillSyncWorker(db=fake_db).run(document_id=document_id)

    assert result["status"] == "payment_ready"
    assert result["erp_bill_id"] == "ERP-BILL-1"
    assert provider.calls == 1


async def test_worker_rolls_back_when_timeout_persisted_nothing(worker_env, fake_db, monkeypatch):
    document_id, _ = seed_document(fake_db, status="approved")
    provider = FakeProvider(
        fake_db,
        persist=False,
        error=httpx.TimeoutException("provider timed out before accepting the bill"),
    )

    async def fake_provider(_org_id, _db=None):
        return provider

    monkeypatch.setattr(worker_env, "get_accounting_provider", fake_provider)

    with pytest.raises(httpx.TimeoutException):
        await worker_env.BillSyncWorker(db=fake_db).run(document_id=document_id)

    row = fake_db.table("documents").select("*").eq("id", str(document_id)).single().execute().data
    assert row["ap_status"] == "approved"
    assert row["erp_bill_id"] is None
    assert provider.calls == 1
