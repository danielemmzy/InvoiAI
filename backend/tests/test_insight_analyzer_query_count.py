"""Insight analyzers must query per report, not per vendor or status."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.insights.analyzers.payable_analyzer import PayableAnalyzer
from app.services.insights.analyzers.vendor_analyzer import VendorAnalyzer


class Vendors:
    def __init__(self, count: int):
        self.count = count

    async def top_vendors_by_spend(self, _org_id, limit=10):
        return [
            SimpleNamespace(
                id=uuid4(),
                name=f"Vendor {index}",
                average_spend=100,
                stddev_spend=10,
                total_document_count=5,
            )
            for index in range(self.count)
        ]


class Documents:
    def __init__(self):
        self.batch_calls = 0
        self.per_vendor_calls = 0

    async def latest_documents_by_vendor(self, _org_id, vendor_ids, per_vendor=1):
        self.batch_calls += 1
        self.requested = list(vendor_ids)
        return {
            str(vendor_id): [
                SimpleNamespace(
                    total_amount=120,
                    vendor_id=vendor_id,
                    created_at=datetime.now(UTC),
                )
            ]
            for vendor_id in vendor_ids
        }

    async def list_vendor_documents(self, *_args, **_kwargs):  # pragma: no cover - regression
        self.per_vendor_calls += 1
        raise AssertionError("vendors must not be queried individually")

    async def list_by_statuses(self, _org_id, statuses, limit=200):
        self.batch_calls += 1
        self.statuses = list(statuses)
        return []

    async def list_by_status(self, *_args, **_kwargs):  # pragma: no cover - regression
        raise AssertionError("statuses must be fetched in one query")


@pytest.mark.parametrize("vendor_count", [1, 20])
@pytest.mark.asyncio
async def test_vendor_analyzer_uses_one_document_query(vendor_count):
    documents = Documents()
    analyzer = VendorAnalyzer(Vendors(vendor_count), documents)

    result = await analyzer.run(uuid4())

    assert len(result.data["increases"]) == vendor_count
    assert documents.batch_calls == 1
    assert documents.per_vendor_calls == 0
    assert len(documents.requested) == vendor_count


@pytest.mark.asyncio
async def test_payable_analyzer_fetches_all_statuses_in_one_query():
    documents = Documents()
    analyzer = PayableAnalyzer(documents)

    await analyzer.run(uuid4())

    assert documents.batch_calls == 1
    assert len(documents.statuses) == 3
