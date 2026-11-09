"""The routing engine must load rules from the real repository contract.

`ApprovalRuleRepository.list()` returns dictionaries. The engine matches
against `ApprovalRule`, so the bridge used to crash with
`AttributeError: list_active_rules` before any workflow could start.
"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.core.enum.ap import ApprovalRuleScope
from app.services.ap.routing_engine import APRoutingEngine

ORG = UUID("00000000-0000-0000-0000-0000000000aa")


class _FakeRules:
    def __init__(self, rows):
        self.rows = rows
        self.calls: list[tuple] = []

    async def list(self, org_id, *, scope=None, active_only=True):
        self.calls.append((org_id, scope, active_only))
        return self.rows


def _row(**overrides):
    now = datetime.now(UTC).isoformat()
    row = {
        "id": str(uuid4()),
        "org_id": str(ORG),
        "created_at": now,
        "updated_at": now,
        "name": "Auto approve small bills",
        "scope": "bill",
        "approver_type": "role",
        "approver_role": "approver",
        "actions": [{"type": "auto_approve", "reason": "below threshold"}],
    }
    row.update(overrides)
    return row


@pytest.mark.asyncio
async def test_build_plan_loads_active_rules_for_the_scope():
    rules = _FakeRules([_row()])
    engine = APRoutingEngine(db=object(), rules=rules, members=object())

    plan, mode, decision = await engine.build_plan(
        org_id=ORG,
        amount=Decimal("50"),
        scope=ApprovalRuleScope.BILL,
    )

    assert rules.calls == [(ORG, "bill", True)]
    assert plan == []
    assert mode == "sequential"
    assert decision is not None
    assert decision.decision == "approve"


@pytest.mark.asyncio
async def test_null_defaulted_columns_fall_back_to_model_defaults():
    rules = _FakeRules(
        [
            _row(
                priority=None,
                step_name=None,
                step_number=None,
                execution_mode=None,
                is_active=None,
                scope="bill",
            )
        ]
    )
    engine = APRoutingEngine(db=object(), rules=rules, members=object())

    _plan, _mode, decision = await engine.build_plan(
        org_id=ORG,
        amount=Decimal("50"),
        scope=ApprovalRuleScope.BILL,
    )

    assert decision is not None
    assert decision.decision == "approve"


@pytest.mark.asyncio
async def test_unknown_database_columns_are_ignored():
    rules = _FakeRules([_row(future_column="ignored")])
    engine = APRoutingEngine(db=object(), rules=rules, members=object())

    _plan, _mode, decision = await engine.build_plan(
        org_id=ORG,
        amount=Decimal("50"),
        scope=ApprovalRuleScope.BILL,
    )

    assert decision is not None


class _FallbackQuery:
    """Minimal Supabase query that rejects enum filters in SQL."""

    def __init__(self, db):
        self.db = db

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, field, values):
        raise AssertionError(f"role filter {values!r} would reach the database enum")

    def execute(self):
        return SimpleNamespace(data=self.db.rows)


class _FallbackDb:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        assert name == "org_members"
        return _FallbackQuery(self)


@pytest.mark.asyncio
async def test_fallback_does_not_send_unsupported_roles_to_the_database():
    owner_id = uuid4()
    db = _FallbackDb(
        [
            {
                "user_id": str(owner_id),
                "role": "owner",
                "spending_limit": None,
                "payment_approval_limit": None,
            },
            {
                "user_id": str(uuid4()),
                "role": "member",
                "spending_limit": None,
                "payment_approval_limit": None,
            },
        ]
    )
    engine = APRoutingEngine(
        db=db,
        rules=_FakeRules([]),
        members=object(),
    )

    plan, mode, decision = await engine.build_plan(
        org_id=ORG,
        amount=Decimal("957"),
        scope=ApprovalRuleScope.BILL,
    )

    assert decision is None
    assert mode == "sequential"
    assert len(plan) == 1
    assert plan[0].approver_id == owner_id
    assert plan[0].metadata == {"fallback": True}
