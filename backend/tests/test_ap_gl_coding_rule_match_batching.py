"""GL coding must update rule match counters once per document, atomically.

The old flow issued one ``increment_coding_rule_match`` RPC per matched line,
so a 40-line invoice that matched one rule made 40 counter round trips.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.core.enum.ap import APCodingSource
from app.models.domain.ap import CodingRule
from app.repositories.ap.coding_repository import CodingRuleRepository
from app.services.ap.gl_coding_service import GLCodingService

ORG_ID = UUID("00000000-0000-0000-0000-0000000000aa")


def _rule(**kwargs):
    now = datetime.now(UTC)
    rule_id = kwargs.pop("id", uuid4())
    return CodingRule(
        id=rule_id,
        org_id=ORG_ID,
        priority=100,
        created_at=now,
        updated_at=now,
        **kwargs,
    )


class FakeRules:
    def __init__(self, rules):
        self.rules = rules
        self.batch_calls: list[list[UUID]] = []
        self.single_calls: list[UUID] = []

    async def list_active(self, _org_id):
        return self.rules

    async def increment_match_counts(self, rule_ids):
        self.batch_calls.append(list(rule_ids))

    async def increment_match_count(self, rule_id):  # pragma: no cover - regression path
        self.single_calls.append(rule_id)
        raise AssertionError("match counters must not be written per line")


class FakeQuery:
    def update(self, _payload):
        return self

    def eq(self, *_args, **_kwargs):
        return self


class FakeDatabase:
    def table(self, _name):
        return FakeQuery()


class FakeCodings:
    def __init__(self):
        self.db = FakeDatabase()
        self.saved = []

    async def save_codings(self, codings):
        self.saved.extend(codings)
        return codings


@pytest.mark.asyncio
async def test_counter_is_written_once_per_document_not_per_line(monkeypatch):
    import app.services.ap.gl_coding_service as coding_module

    async def noop_execute(*_args, **_kwargs):
        return SimpleNamespace(data=[])

    monkeypatch.setattr(coding_module, "execute", noop_execute)

    account_id = uuid4()
    rule = _rule(description_pattern="cloud", gl_account_id=account_id)
    rules = FakeRules([rule])

    service = GLCodingService.__new__(GLCodingService)
    service.rules = rules
    service.coa = SimpleNamespace(
        list_by_org=lambda _org_id: _async(
            [
                SimpleNamespace(
                    id=account_id,
                    is_postable=True,
                    account_code="5000",
                    account_name="Office costs",
                )
            ]
        )
    )
    service.codings = FakeCodings()
    service.ai = SimpleNamespace()

    line_items = [
        {"id": uuid4(), "description": f"Cloud subscription {index}", "amount": "10.00"}
        for index in range(6)
    ]

    codings = await service.code_document(
        org_id=ORG_ID,
        document_id=uuid4(),
        line_items=line_items,
        vendor_id=None,
    )

    assert len(codings) == 6
    assert all(coding.source == APCodingSource.RULE for coding in codings)
    # One aggregated call carrying every matched line's rule.
    assert len(rules.batch_calls) == 1
    assert rules.batch_calls[0] == [rule.id] * 6
    assert rules.single_calls == []


async def _async(value):
    return value


class RecordingRpc:
    def __init__(self, recorder, name, params, error_for):
        self.recorder = recorder
        self.name = name
        self.params = params
        self.error_for = error_for

    def execute(self):
        self.recorder.append((self.name, self.params))
        error = self.error_for(self.name)
        if error is not None:
            raise error
        return SimpleNamespace(data=[], count=0)


class RecordingRpcDatabase:
    def __init__(self, error=None, error_function=None):
        self.calls = []
        self.error = error
        self.error_function = error_function or (lambda _name: True)

    def rpc(self, name, params):
        error = self.error if self.error_function(name) else None
        return RecordingRpc(self.calls, name, params, lambda _name: error)


class MissingFunctionError(Exception):
    code = "PGRST202"
    message = "Could not find the function public.increment_coding_rule_matches"


@pytest.mark.asyncio
async def test_repository_aggregates_counts_into_one_rpc():
    database = RecordingRpcDatabase()
    repository = object.__new__(CodingRuleRepository)
    repository.db = database
    first, second = uuid4(), uuid4()

    await repository.increment_match_counts([first, first, first, second])

    assert len(database.calls) == 1
    name, params = database.calls[0]
    assert name == "increment_coding_rule_matches"
    assert sorted(params["p_counts"], key=lambda entry: entry["rule_id"]) == sorted(
        [
            {"rule_id": str(first), "count": 3},
            {"rule_id": str(second), "count": 1},
        ],
        key=lambda entry: entry["rule_id"],
    )


@pytest.mark.asyncio
async def test_missing_batched_function_falls_back_to_one_rpc_per_rule():
    database = RecordingRpcDatabase(
        error=MissingFunctionError(),
        # Only the not-yet-deployed batched function is missing.
        error_function=lambda name: name == "increment_coding_rule_matches",
    )
    repository = object.__new__(CodingRuleRepository)
    repository.db = database
    first, second = uuid4(), uuid4()

    await repository.increment_match_counts([first, first, second])

    names = [name for name, _ in database.calls]
    assert names[0] == "increment_coding_rule_matches"
    assert sorted(names[1:]) == ["increment_coding_rule_match", "increment_coding_rule_match"]
    fallback_rule_ids = sorted(params["rule_id"] for _, params in database.calls[1:])
    assert fallback_rule_ids == sorted([str(first), str(second)])


@pytest.mark.asyncio
async def test_unexpected_rpc_failures_are_not_swallowed():
    database = RecordingRpcDatabase(error=RuntimeError("permission denied for function"))
    repository = object.__new__(CodingRuleRepository)
    repository.db = database

    with pytest.raises(RuntimeError):
        await repository.increment_match_counts([uuid4()])
