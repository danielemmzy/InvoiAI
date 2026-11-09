import base64
import hashlib
import hmac
import time
from types import SimpleNamespace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.ap.email_intake_service import EmailIntakeService


class Query:
    def __init__(self, db, table):
        self.db, self.table_name = db, table
        self.filters, self.action, self.payload = [], "select", None

    def select(self, *args): return self
    def eq(self, key, value): self.filters.append(("eq", key, value)); return self
    def gte(self, key, value): self.filters.append(("gte", key, value)); return self
    def limit(self, value): return self
    def insert(self, payload): self.action, self.payload = "insert", payload; return self
    def update(self, payload): self.action, self.payload = "update", payload; return self
    def execute(self):
        rows = self.db.tables.setdefault(self.table_name, [])
        def matches(row):
            for op, key, value in self.filters:
                if op == "eq" and str(row.get(key)) != str(value): return False
                if op == "gte" and (row.get(key) is None or str(row[key]) < str(value)): return False
            return True
        matches = [r for r in rows if matches(r)]
        if self.action == "insert":
            payload = dict(self.payload)
            payload.setdefault("id", str(uuid4()))
            rows.append(payload)
            return SimpleNamespace(data=[payload])
        if self.action == "update":
            for row in matches: row.update(self.payload)
        return SimpleNamespace(data=matches)


class DB:
    def __init__(self, rows): self.tables = rows
    def table(self, name): return Query(self, name)


class Upload:
    def __init__(self): self.calls = []
    async def upload(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(id=uuid4())


@pytest.fixture
def intake():
    org_id = str(uuid4())
    db = DB({"ap_email_intake_addresses": [{"id": str(uuid4()), "org_id": org_id,
        "email_address": "ap+workspace@inbound.invoiai.com", "is_active": True}]})
    upload = Upload()
    return EmailIntakeService(upload, db), db, upload


def message(**overrides):
    data = {"to_address": "ap+workspace@inbound.invoiai.com", "sender": "vendor@example.com",
        "subject": "Invoice", "message_id": "<msg-1>",
        "attachments": [{"filename": "invoice.pdf", "content_type": "application/pdf",
                         "content_base64": base64.b64encode(b"%PDF-1.7 sample").decode()}],
        "auth_results": {"spf": "pass", "dkim": "pass", "dmarc": "pass"}}
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_email_auth_failure_is_quarantined_and_recorded(intake):
    service, db, upload = intake
    result = await service.ingest(**message(auth_results={"spf": "fail", "dkim": "pass", "dmarc": "fail"}))
    assert result["documents"]
    assert upload.calls[0]["email_auth_failure"] == {"spf": "fail", "dmarc": "fail"}
    assert db.tables["ap_email_intake_events"][0]["metadata"]["auth_results"]["spf"] == "fail"


@pytest.mark.asyncio
async def test_invalid_recipient_and_oversized_message_are_rejected(intake):
    service, _, _ = intake
    with pytest.raises(ValueError, match="Unknown or inactive"):
        await service.ingest(**message(to_address="other@inbound.invoiai.com"))
    with pytest.raises(ValueError, match="single exact"):
        await service.ingest(**message(to_address=" ap+workspace@inbound.invoiai.com"))
    with pytest.raises(ValueError, match="message exceeds"):
        await service.ingest(**message(attachments=[{"content_base64": "A" * (35 * 1024 * 1024)}]))


@pytest.mark.asyncio
async def test_sender_and_attachment_count_limits_are_enforced(intake):
    service, _, _ = intake
    with pytest.raises(ValueError, match="Sender"):
        await service.ingest(**message(sender="x" * 1025))
    with pytest.raises(ValueError, match="between 1 and"):
        await service.ingest(**message(attachments=[{}] * 26))


@pytest.mark.asyncio
async def test_org_hourly_intake_limit_is_enforced(intake):
    service, db, upload = intake
    org_id = db.tables["ap_email_intake_addresses"][0]["org_id"]
    recent = datetime.now(timezone.utc).isoformat()
    db.tables["ap_email_intake_events"] = [{"org_id": org_id, "created_at": recent} for _ in range(100)]
    with pytest.raises(ValueError, match="rate limit"):
        await service.ingest(**message())
    assert upload.calls == []


@pytest.mark.asyncio
async def test_sender_hourly_intake_limit_is_enforced(intake):
    service, db, upload = intake
    org_id = db.tables["ap_email_intake_addresses"][0]["org_id"]
    recent = datetime.now(timezone.utc).isoformat()
    db.tables["ap_email_intake_events"] = [
        {"org_id": org_id, "sender_email": "vendor@example.com", "created_at": recent}
        for _ in range(20)
    ]
    with pytest.raises(ValueError, match="Sender email intake rate limit"):
        await service.ingest(**message())
    assert upload.calls == []


@pytest.mark.asyncio
async def test_repeated_provider_message_is_idempotent(intake):
    service, _, upload = intake
    payload = message()
    first = await service.ingest(**payload)
    second = await service.ingest(**payload)
    assert len(first["documents"]) == 1
    assert second == {"duplicate": True, "documents": []}
    assert len(upload.calls) == 1


def test_webhook_signature_requires_fresh_timestamp(monkeypatch):
    import app.routers.ap_email as router

    monkeypatch.setattr(router.settings, "ap_email_webhook_secret", "test-secret")
    raw = b'{"message_id":"m"}'
    timestamp = str(1_800_000_000)
    signature = hmac.new(b"test-secret", timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    assert router.valid_webhook_signature(raw, signature, timestamp, now=1_800_000_000)
    assert not router.valid_webhook_signature(raw, signature, timestamp, now=1_800_000_301)
    assert not router.valid_webhook_signature(raw, signature, "bad", now=1_800_000_000)


def test_inbound_route_rejects_stale_signed_delivery(client, monkeypatch):
    import app.routers.ap_email as router

    monkeypatch.setattr(router.settings, "ap_email_webhook_secret", "test-secret")
    raw = b'{"to":"ap@example.com","message_id":"m"}'
    timestamp = str(int(time.time()) - 301)
    signature = hmac.new(b"test-secret", timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    response = client.post("/api/v2/ap/email/inbound", content=raw, headers={
        "X-InvoiAI-Email-Timestamp": timestamp, "X-InvoiAI-Email-Signature": signature,
    })
    assert response.status_code == 401
