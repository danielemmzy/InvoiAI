from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.vendor.vendor_import_service import VendorImportService
from app.services.vendor.vendor_service import VendorService
from app.schemas.vendor import VendorUpdate


class FakeProvider:
    name = "xero"

    async def sync(self):
        return {"imported": 2, "updated": 1, "total": 3, "skipped": 0, "failed": 1,
                "errors": [{"resource": "vendor", "external_id": "c-4", "error": "MappingError"}]}


class ConnectionQuery:
    def __init__(self, db):
        self.db = db
        self.filters = {}
        self.operation = "select"
        self.payload = None

    def select(self, *_args):
        return self

    def update(self, payload):
        self.operation, self.payload = "update", payload
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def limit(self, _limit):
        return self

    def execute(self):
        rows = [row for row in self.db.connections if all(str(row.get(k)) == str(v) for k,v in self.filters.items())]
        if self.operation == "update":
            for row in rows:
                row.update(self.payload)
        return SimpleNamespace(data=rows)


class ConnectionDb:
    def __init__(self):
        self.connections = [{"id": "connection-1", "org_id": "org", "provider": "xero", "is_active": True, "metadata": {}}]

    def table(self, _table):
        return ConnectionQuery(self)


async def test_supplier_import_uses_explicit_provider_and_organization():
    org_id = uuid4()
    calls = []

    async def resolve_provider(*, org_id, provider, db):
        calls.append((org_id, provider, db))
        return FakeProvider()

    db = ConnectionDb()
    db.connections[0]["org_id"] = str(org_id)
    service = VendorImportService(db=db, provider_resolver=resolve_provider)

    result = await service.import_suppliers(org_id=org_id, provider="xero")

    assert result["imported"] == 2
    assert result["updated"] == 1
    assert calls[0][0:2] == (org_id, "xero")
    summary = db.connections[0]["metadata"]["supplier_import"]
    assert summary["counts"] == {"total": 3, "imported": 2, "updated": 1, "skipped": 0, "failed": 1}
    assert summary["errors"] == [{"resource": "vendor", "external_id": "c-4", "error": "MappingError"}]
    assert summary["completed_at"]


async def test_supplier_import_rejects_provider_mismatch():
    async def resolve_provider(**_kwargs):
        return FakeProvider()

    service = VendorImportService(db=object(), provider_resolver=resolve_provider)

    with pytest.raises(ValueError, match="does not match"):
        await service.import_suppliers(org_id=uuid4(), provider="quickbooks")


async def test_vendor_deactivation_is_a_soft_update():
    vendor_id = uuid4()

    class Repository:
        updated = None

        async def get(self, _vendor_id):
            return SimpleNamespace(id=vendor_id)

        async def update(self, record_id, values):
            self.updated = (record_id, values)
            return SimpleNamespace(id=record_id)

    repository = Repository()

    assert await VendorService(repository).delete_vendor(vendor_id)
    assert repository.updated == (vendor_id, {"is_active": False})


async def test_vendor_rename_updates_normalized_name():
    vendor_id = uuid4()

    class Repository:
        async def get(self, _vendor_id):
            return SimpleNamespace(id=vendor_id)

        async def update(self, _record_id, values):
            return values

    updated = await VendorService(Repository()).update_vendor(
        vendor_id,
        VendorUpdate(name="  Acme Supplies  "),
    )

    assert updated == {"name": "Acme Supplies", "normalized_name": "acme supplies"}
