"""Query-count regression test for a vendor's credit-note list.

The vendor detail page fetched applications and events once per credit note.
Its query count must stay flat as the number of credits grows.
"""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.vendor.vendor_credit_service import VendorCreditService


class Query:
    def __init__(self, database, table_name):
        self.database = database
        self.table_name = table_name
        self.operation = "select"
        self.payload = None
        self.wanted_ids = None

    def select(self, *_args, **_kwargs): return self
    def eq(self, *_args, **_kwargs): return self
    def in_(self, column, values):
        self.wanted_ids = (column, {str(value) for value in values})
        return self
    def order(self, *_args, **_kwargs): return self
    def limit(self, *_args, **_kwargs): return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def execute(self):
        self.database.executed.append((self.table_name, self.operation))
        if self.operation == "update":
            return SimpleNamespace(data=[self.payload])
        return SimpleNamespace(data=self.database.rows_for(self.table_name, self.wanted_ids))


class Database:
    def __init__(self, credit_count: int):
        self.executed = []
        self.vendor_id = str(uuid4())
        self.credits = [
            {
                "id": str(uuid4()),
                "vendor_id": self.vendor_id,
                "status": "open",
                "amount": "100.00",
                "remaining_amount": "100.00",
                "expires_at": (
                    (date.today() - timedelta(days=1)).isoformat()
                    if index == 0
                    else (date.today() + timedelta(days=30)).isoformat()
                ),
            }
            for index in range(credit_count)
        ]
        self.applications = [
            {
                "id": str(uuid4()),
                "vendor_credit_id": credit["id"],
                "document_id": str(uuid4()),
                "amount": "10.00",
            }
            for credit in self.credits
        ]
        self.events = [
            {
                "id": str(uuid4()),
                "vendor_credit_id": credit["id"],
                "event_type": "created",
                "created_at": datetime.now(UTC).isoformat(),
            }
            for credit in self.credits
        ]

    def table(self, name):
        return Query(self, name)

    def rows_for(self, table_name, wanted_ids):
        if table_name == "vendors":
            return [{"id": self.vendor_id, "name": "Supplier"}]
        if table_name == "vendor_credits":
            return self.credits
        if table_name == "vendor_credit_applications":
            wanted = wanted_ids[1] if wanted_ids else {c["id"] for c in self.credits}
            return [row for row in self.applications if row["vendor_credit_id"] in wanted]
        if table_name == "vendor_credit_events":
            wanted = wanted_ids[1] if wanted_ids else {c["id"] for c in self.credits}
            return [row for row in self.events if row["vendor_credit_id"] in wanted]
        raise AssertionError(f"Unexpected table queried: {table_name}")


@pytest.mark.parametrize("credit_count", [1, 15])
@pytest.mark.asyncio
async def test_vendor_credit_list_query_count_is_constant(credit_count):
    database = Database(credit_count)
    service = VendorCreditService(db=database)

    credits = await service.list_for_vendor(uuid4(), uuid4())

    assert len(credits) == credit_count
    # The applications/events reads run concurrently, so only assert the set
    # of round trips, not their interleaving.
    assert sorted(database.executed) == sorted([
        ("vendors", "select"),
        ("vendor_credits", "select"),
        ("vendor_credits", "update"),
        ("vendor_credit_applications", "select"),
        ("vendor_credit_events", "select"),
    ])
    assert credits[0]["status"] == "expired"
    assert all(credit["applications"] for credit in credits)
    assert all(credit["events"] for credit in credits)
