"""Starter chart-of-accounts seeding.

The seed must be idempotent: running it twice may not duplicate accounts,
and it may never touch accounts the organization already configured.
"""

from types import SimpleNamespace
from uuid import UUID

import pytest

from app.services.ap.chart_of_accounts_seed import (
    STARTER_ACCOUNTS,
    missing_starter_accounts,
    seed_starter_chart_of_accounts,
)

ORG = UUID("00000000-0000-0000-0000-000000000001")


class _Query:
    def __init__(self, db):
        self.db = db
        self._insert = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def insert(self, payload):
        self._insert = payload
        return self

    def execute(self):
        if self._insert is not None:
            rows = self._insert if isinstance(self._insert, list) else [self._insert]
            self.db.inserted.extend(rows)
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=[{"account_code": code} for code in self.db.existing_codes])


class _FakeDb:
    def __init__(self, existing_codes=()):
        self.existing_codes = list(existing_codes)
        self.inserted = []

    def table(self, _name):
        return _Query(self)


def test_starter_accounts_are_unique_and_classified():
    codes = [account["account_code"] for account in STARTER_ACCOUNTS]
    assert len(codes) == len(set(codes))
    assert all(account["account_name"] for account in STARTER_ACCOUNTS)
    assert all(account["account_type"] for account in STARTER_ACCOUNTS)
    assert {"expense", "asset", "liability"} <= {account["account_type"] for account in STARTER_ACCOUNTS}


def test_missing_starter_accounts_skips_configured_codes():
    missing = missing_starter_accounts({account["account_code"] for account in STARTER_ACCOUNTS[:5]})
    assert len(missing) == len(STARTER_ACCOUNTS) - 5
    assert missing[0]["account_code"] == STARTER_ACCOUNTS[5]["account_code"]


@pytest.mark.asyncio
async def test_seed_is_idempotent_and_never_duplicates():
    db = _FakeDb(existing_codes=[account["account_code"] for account in STARTER_ACCOUNTS])
    result = await seed_starter_chart_of_accounts(ORG, db=db)

    assert result == {"created": 0, "skipped": len(STARTER_ACCOUNTS)}
    assert db.inserted == []


@pytest.mark.asyncio
async def test_seed_inserts_missing_accounts_with_org_scope():
    db = _FakeDb(existing_codes=[])
    result = await seed_starter_chart_of_accounts(ORG, db=db)

    assert result == {"created": len(STARTER_ACCOUNTS), "skipped": 0}
    assert len(db.inserted) == len(STARTER_ACCOUNTS)
    assert {row["org_id"] for row in db.inserted} == {str(ORG)}
    assert {row["source"] for row in db.inserted} == {"starter"}
