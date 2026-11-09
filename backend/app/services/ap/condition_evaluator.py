"""
============================================================
AP Condition Evaluator

Evaluates a rule's `conditions` tree against a context dict built
by the caller (APRoutingEngine). Pure and side-effect free — no
DB access, easy to unit test in isolation.

Tree shape
----------
Leaf:
    {"field": "amount", "op": "gt", "value": 5000}

Group:
    {"op": "and" | "or", "conditions": [<node>, ...]}
    {"op": "not", "conditions": [<node>]}   # exactly one child

Leaf operators
--------------
eq, neq        — equality/inequality (case-insensitive for strings)
gt, gte, lt, lte — numeric/date comparison
in             — context value is a member of `value` (a list)
contains       — `value` is a member of the context value (a list)
exists         — field is present and not None in context (value ignored)

A leaf whose `field` is absent from the context evaluates to False
for every operator except a negated `exists` check — rules should
be written expecting "unknown" to mean "doesn't match" rather than
raising, since not every context field is resolvable for every
document (e.g. payment_method is only known for payment-scope
rules).
============================================================
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

_LEAF_OPS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "contains", "exists"}
_GROUP_OPS = {"and", "or", "not"}


class ConditionError(ValueError):
    pass


def evaluate(node: dict[str, Any] | None, context: dict[str, Any]) -> bool:
    if not node:
        return True  # an empty/absent tree matches everything, same as no flat filters set

    if "conditions" in node:
        return _evaluate_group(node, context)

    if "field" in node:
        return _evaluate_leaf(node, context)

    raise ConditionError(f"Condition node must have either 'conditions' (group) or 'field' (leaf): {node!r}")


def _evaluate_group(node: dict[str, Any], context: dict[str, Any]) -> bool:
    op = node.get("op", "and")
    if op not in _GROUP_OPS:
        raise ConditionError(f"Unknown group operator {op!r}; expected one of {_GROUP_OPS}")

    children = node.get("conditions") or []
    if not isinstance(children, list) or not children:
        raise ConditionError("A group condition requires a non-empty 'conditions' list.")

    if op == "not":
        if len(children) != 1:
            raise ConditionError("A 'not' group requires exactly one child condition.")
        return not evaluate(children[0], context)

    if op == "and":
        return all(evaluate(child, context) for child in children)

    return any(evaluate(child, context) for child in children)  # op == "or"


def _evaluate_leaf(node: dict[str, Any], context: dict[str, Any]) -> bool:
    field = node["field"]
    op = node.get("op", "eq")
    expected = node.get("value")

    if op not in _LEAF_OPS:
        raise ConditionError(f"Unknown leaf operator {op!r}; expected one of {_LEAF_OPS}")

    present = field in context and context[field] is not None
    actual = context.get(field)

    if op == "exists":
        return present if expected is None or expected is True else not present

    if not present:
        return False

    if op == "eq":
        return _normalize(actual) == _normalize(expected)
    if op == "neq":
        return _normalize(actual) != _normalize(expected)

    if op in ("gt", "gte", "lt", "lte"):
        try:
            a, b = _to_number(actual), _to_number(expected)
        except (TypeError, ValueError, InvalidOperation) as exc:
            raise ConditionError(f"Cannot compare non-numeric values for field {field!r}: {actual!r} {op} {expected!r}") from exc
        return {"gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b}[op]

    if op == "in":
        if not isinstance(expected, (list, tuple, set)):
            raise ConditionError(f"'in' requires a list value, got {expected!r}")
        return _normalize(actual) in {_normalize(v) for v in expected}

    if op == "contains":
        if isinstance(actual, (list, tuple, set)):
            return _normalize(expected) in {_normalize(v) for v in actual}
        return False

    raise ConditionError(f"Unhandled leaf operator {op!r}")  # unreachable given _LEAF_OPS check above


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _to_number(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise TypeError("bool is not a valid numeric comparison value")
    return Decimal(str(value))


def validate(node: dict[str, Any] | None) -> None:
    """Raises ConditionError if the tree is structurally invalid. Does not need a context."""
    if not node:
        return
    evaluate(node, {})
