"""Matching exceptions must be idempotent across retries.

A crash-recovery sweep can re-run matching for the same invoice. The same
price/quantity finding must refresh the existing exception, not create a second
copy that a reviewer has to resolve twice.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.core.enum.ap import APExceptionStatus, APExceptionType
from app.models.domain.ap import InvoiceException
from app.repositories.ap.exception_repository import InvoiceExceptionRepository

ORG = UUID("00000000-0000-0000-0000-000000000001")
DOC = UUID("00000000-0000-0000-0000-000000000002")


class _Query:
    def __init__(self, db):
        self.db = db
        self._insert = None
        self._update = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def insert(self, payload):
        self._insert = payload
        return self

    def update(self, payload):
        self._update = payload
        return self

    def execute(self):
        if self._insert is not None:
            self.db.inserts += 1
            self.db.inserted = self._insert
            return SimpleNamespace(data=[{**self.db.row, **self._insert}])
        if self._update is not None:
            self.db.updates += 1
            self.db.updated = self._update
            return SimpleNamespace(data=[{**self.db.row, **self._update}])
        return SimpleNamespace(data=[{"id": str(self.db.row["id"])}] if self.db.has_open else [])


class _FakeDb:
    def __init__(self, *, has_open: bool):
        self.has_open = has_open
        self.inserts = 0
        self.updates = 0
        self.inserted = None
        self.updated = None
        self.row = {
            "id": str(uuid4()),
            "org_id": str(ORG),
            "document_id": str(DOC),
            "exception_type": APExceptionType.PRICE_MISMATCH.value,
            "status": APExceptionStatus.IN_REVIEW.value,
            "severity": "critical",
            "title": "Price mismatch",
            "details": {},
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

    def table(self, _name):
        return _Query(self)


def _exception() -> InvoiceException:
    now = datetime.now(UTC)
    return InvoiceException(
        id=uuid4(),
        org_id=ORG,
        document_id=DOC,
        exception_type=APExceptionType.PRICE_MISMATCH,
        severity="critical",
        title="Price mismatch",
        expected_value="10.00",
        actual_value="12.00",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_existing_open_exception_is_refreshed_not_duplicated():
    db = _FakeDb(has_open=True)
    repo = InvoiceExceptionRepository()
    repo.db = db

    result = await repo.upsert_open(_exception())

    assert result is not None
    assert db.updates == 1
    assert db.inserts == 0
    # A reviewer may already have moved it to in_review; retrying matching must
    # not silently reset that status to "open".
    assert "status" not in db.updated


@pytest.mark.asyncio
async def test_missing_exception_is_created():
    db = _FakeDb(has_open=False)
    repo = InvoiceExceptionRepository()
    repo.db = db

    result = await repo.upsert_open(_exception())

    assert result is not None
    assert db.inserts == 1
    assert db.updates == 0
    assert db.inserted["exception_type"] == APExceptionType.PRICE_MISMATCH.value
