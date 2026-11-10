from types import SimpleNamespace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.enum.ap import APCodingSource
from app.models.domain.ap import CodingRule
from app.services.ap.gl_coding_service import GLCodingService
from app.services.ap.provider.accounting_provider import (
    AmbiguousAccountingProviderError,
    get_accounting_provider,
)


@pytest.mark.asyncio
async def test_exact_vendor_rule_precedes_description_pattern():
    org_id, document_id, vendor_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    vendor_account, pattern_account = uuid4(), uuid4()
    vendor_rule = CodingRule(
        id=uuid4(), org_id=org_id, vendor_id=vendor_id,
        gl_account_id=vendor_account, priority=100, created_at=now, updated_at=now,
    )
    pattern_rule = CodingRule(
        id=uuid4(), org_id=org_id, description_pattern="cloud",
        gl_account_id=pattern_account, priority=1, created_at=now, updated_at=now,
    )

    class Rules:
        async def increment_match_count(self, _rule_id):
            pass

    service = GLCodingService.__new__(GLCodingService)
    service.rules = Rules()
    coding = await service._code_line(
        org_id, document_id,
        {"id": uuid4(), "description": "Cloud subscription"},
        vendor_id,
        [pattern_rule, vendor_rule],
        [],
    )

    assert coding.gl_account_id == vendor_account
    assert coding.source == APCodingSource.RULE
    assert coding.reasoning == "Matched the exact supplier coding rule."


def test_rule_pattern_requires_description_or_sku_match():
    rule = SimpleNamespace(
        vendor_id=None, description_pattern="software", sku_pattern="S-1"
    )

    assert not GLCodingService._rule_matches(rule, {"description": "Other"}, None)
    assert GLCodingService._rule_matches(rule, {"sku": "s-1"}, None)


@pytest.mark.asyncio
async def test_provider_dispatch_uses_only_the_explicit_active_connection():
    class Query:
        def __init__(self, rows):
            self.rows = rows

        def select(self, *_args):
            return self

        def eq(self, key, value):
            self.rows = [row for row in self.rows if str(row.get(key)) == str(value)]
            return self

        def execute(self):
            return SimpleNamespace(data=self.rows)

    class Db:
        def __init__(self, rows):
            self.rows = rows

        def table(self, _name):
            return Query(list(self.rows))

    org_id = uuid4()
    active = {"id": "selected", "org_id": str(org_id), "provider": "quickbooks", "is_active": True}
    inactive = {"id": "old", "org_id": str(org_id), "provider": "xero", "is_active": False}
    provider = await get_accounting_provider(org_id, Db([inactive, active]))
    assert provider.connection_id == "selected"

    with pytest.raises(AmbiguousAccountingProviderError):
        await get_accounting_provider(
            org_id,
            Db([active, {**active, "id": "second", "provider": "xero"}]),
        )
