"""
============================================================
AP Routing Engine

Turns a document's context (amount, vendor, department, cost
center, location, document type, risk level, PO requirement)
into an ordered approval plan by evaluating an organization's
active ap_approval_rules, in priority order.

This is what the naive "pick the first active owner/admin/
approver" logic in approval_bridge.py used to do unconditionally.
That behaviour is preserved here as the fallback when no rule
matches, so a document is never stuck without an approver.

Responsibilities
----------------
- Match rules against a document's context (amount range, vendor,
  department, cost center, location, document type, risk level,
  PO requirement).
- Resolve each matching rule to one approval step: a specific
  user, the first active member with a given role, or an
  approval group (pooled approvers, unresolved until claimed).
- Auto-escalate a user step to that approver's supervisor
  (org_members.supervisor_id) when the document amount exceeds
  the approver's limit, repeating until someone has enough
  authority or the chain runs out.
- Never touch approval_steps/approval_workflows directly —
  callers (approval_bridge.py) persist the returned plan.
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.enum.ap import ApprovalRuleScope, ApproverType
from app.core.enum.database import OrgRole
from app.core.supabase import get_supabase
from app.models.domain.ap import ApprovalRule
from app.models.domain.organization import OrganizationMember
from app.repositories.ap.rules_repository import ApprovalRuleRepository
from app.repositories.organization.member_repository import MemberRepository
from app.services.ap.condition_evaluator import ConditionError, evaluate as evaluate_conditions

MAX_ESCALATION_DEPTH = 5

LEGACY_ROLE_ORDER = [OrgRole.FINANCE_MANAGER.value, OrgRole.AP_MANAGER.value, OrgRole.APPROVER.value, OrgRole.ADMIN.value, OrgRole.OWNER.value]

TERMINAL_ACTION_TYPES = {"block", "auto_approve", "auto_reject"}

# Defaulted columns that must keep their default when the database row has a
# NULL, otherwise Pydantic would reject None for a non-nullable field.
_RULE_NON_NULLABLE = frozenset({
    "is_active",
    "priority",
    "scope",
    "step_number",
    "step_name",
    "execution_mode",
    "approver_type",
})


def approval_rule_from_row(row: dict[str, Any]) -> ApprovalRule:
    """Convert an ``ap_approval_rules`` row into the routing domain model.

    ``ApprovalRuleRepository`` returns plain dictionaries, while the engine
    matches against ``ApprovalRule``. Restricting the payload to model fields
    also keeps future database columns from breaking rule evaluation.
    """
    payload = {
        key: value
        for key, value in row.items()
        if key in ApprovalRule.model_fields
        and not (value is None and key in _RULE_NON_NULLABLE)
    }
    return ApprovalRule.model_validate(payload)


@dataclass
class PlannedStep:
    step_number: int
    step_name: str
    approver_id: UUID | None
    approver_role: str
    approver_group_id: UUID | None
    spending_limit: Decimal | None
    auto_escalated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AutoDecision:
    """
    A terminal action (block / auto_approve / auto_reject) matched
    before any approval steps were built. Callers (approval_bridge.py,
    payment_approval_service.py) check for this and skip workflow
    creation entirely, applying the decision directly.
    """
    decision: str  # "approve" | "reject" | "block"
    reason: str | None
    rule_id: UUID


class APRoutingEngine:

    def __init__(
        self,
        db=None,
        rules: ApprovalRuleRepository | None = None,
        members: MemberRepository | None = None,
    ) -> None:
        self.db = db or get_supabase()
        self.rules = rules or ApprovalRuleRepository()
        self.members = members or MemberRepository()

    # =========================================================
    # Plan
    # =========================================================

    async def build_plan(
        self,
        *,
        org_id: UUID,
        amount: Decimal,
        vendor_id: UUID | None = None,
        department: str | None = None,
        cost_center: str | None = None,
        location: str | None = None,
        document_type: str | None = None,
        risk_level: str | None = None,
        requires_po: bool | None = None,
        scope: ApprovalRuleScope = ApprovalRuleScope.BILL,
        extra_context: dict[str, Any] | None = None,
    ) -> tuple[list[PlannedStep], str, AutoDecision | None]:
        """
        Returns (plan, execution_mode, auto_decision).

        extra_context carries anything beyond the fixed keyword
        arguments above — vendor_verified, exception_status,
        po_match_status, payment_method, line_item_skus, and any
        other field a rule's `conditions` tree references. Unknown
        fields simply don't match (see condition_evaluator.py) rather
        than erroring, so callers only need to populate what they can
        cheaply resolve.

        auto_decision is set when the highest-priority matched rule
        has a terminal action (block / auto_approve / auto_reject) in
        its `actions` list — in that case plan is always [] and the
        caller must NOT create an approval workflow; it applies the
        decision directly instead.
        """

        rule_rows = await self.rules.list(
            org_id,
            scope=scope.value,
            active_only=True,
        )
        rules = [approval_rule_from_row(row) for row in rule_rows]

        context: dict[str, Any] = {
            "amount": amount,
            "vendor_id": str(vendor_id) if vendor_id else None,
            "department": department,
            "cost_center": cost_center,
            "location": location,
            "document_type": document_type,
            "risk_level": risk_level,
            "requires_po": requires_po,
            **(extra_context or {}),
        }

        matched = [rule for rule in rules if self._matches(rule, context)]

        if not matched:
            return (*(await self._legacy_fallback(org_id, amount, scope)), None)

        matched.sort(key=lambda r: (r.step_number, r.priority))

        auto_decision = self._first_terminal_action(matched)
        if auto_decision is not None:
            return [], "sequential", auto_decision

        if any(r.approver_type == ApproverType.GROUP for r in matched):
            execution_mode = "group"
        else:
            execution_mode = matched[0].execution_mode or "sequential"

        limit_field = "payment_approval_limit" if scope == ApprovalRuleScope.PAYMENT else "spending_limit"

        plan: list[PlannedStep] = []
        step_number = 1

        for rule in matched:
            if rule.actions:
                step_number = await self._apply_actions(
                    rule, org_id=org_id, amount=amount, limit_field=limit_field,
                    plan=plan, step_number=step_number,
                )
                continue

            step_number = await self._apply_single_approver(
                rule, org_id=org_id, amount=amount, limit_field=limit_field,
                plan=plan, step_number=step_number,
            )

        if not plan:
            return (*(await self._legacy_fallback(org_id, amount, scope)), None)

        return plan, execution_mode, None

    # =========================================================
    # Terminal actions (block / auto_approve / auto_reject)
    # =========================================================

    @staticmethod
    def _first_terminal_action(matched: list[ApprovalRule]) -> AutoDecision | None:
        for rule in matched:
            for action in rule.actions or []:
                action_type = action.get("type")
                if action_type in TERMINAL_ACTION_TYPES:
                    decision = {"block": "block", "auto_approve": "approve", "auto_reject": "reject"}[action_type]
                    return AutoDecision(decision=decision, reason=action.get("reason"), rule_id=rule.id)
        return None

    # =========================================================
    # Step generation
    # =========================================================

    async def _apply_single_approver(
        self, rule: ApprovalRule, *, org_id: UUID, amount: Decimal, limit_field: str,
        plan: list[PlannedStep], step_number: int,
    ) -> int:
        """Legacy path: one rule -> one approver_type/id/role/group_id -> one (or one escalation chain of) step(s)."""

        if rule.approver_type == ApproverType.GROUP:
            plan.append(PlannedStep(
                step_number=step_number, step_name=rule.step_name, approver_id=None,
                approver_role=OrgRole.APPROVER.value, approver_group_id=rule.approver_group_id,
                spending_limit=None, metadata={"rule_id": str(rule.id)},
            ))
            return step_number + 1

        member = await self._resolve_member(org_id, rule.approver_type, rule.approver_id, rule.approver_role)
        if member is None:
            return step_number

        chain = await self._escalation_chain(org_id, member, amount, limit_field)
        for idx, step_member in enumerate(chain):
            plan.append(PlannedStep(
                step_number=step_number,
                step_name=rule.step_name if idx == 0 else f"{rule.step_name} (escalated)",
                approver_id=step_member.user_id, approver_role=step_member.role,
                approver_group_id=None, spending_limit=getattr(step_member, limit_field),
                auto_escalated=idx > 0, metadata={"rule_id": str(rule.id)},
            ))
            step_number += 1
        return step_number

    async def _apply_actions(
        self, rule: ApprovalRule, *, org_id: UUID, amount: Decimal, limit_field: str,
        plan: list[PlannedStep], step_number: int,
    ) -> int:
        """
        Rule.actions path: an ordered list of add_approver/
        require_approver/route_to_group/escalate/request_review
        actions (block/auto_approve/auto_reject are handled earlier,
        as a terminal short-circuit, and never reach here).
        """

        for action in rule.actions or []:
            action_type = action.get("type")

            if action_type in TERMINAL_ACTION_TYPES:
                continue  # already handled by _first_terminal_action

            if action_type == "route_to_group":
                group_id = action.get("approver_group_id")
                if not group_id:
                    continue
                plan.append(PlannedStep(
                    step_number=step_number, step_name=action.get("step_name") or rule.step_name,
                    approver_id=None, approver_role=OrgRole.APPROVER.value,
                    approver_group_id=UUID(str(group_id)), spending_limit=None,
                    metadata={"rule_id": str(rule.id), "action": action_type},
                ))
                step_number += 1
                continue

            if action_type in ("add_approver", "require_approver", "escalate", "request_review"):
                approver_type = ApproverType(action.get("approver_type", "role"))
                approver_id = UUID(str(action["approver_id"])) if action.get("approver_id") else None
                approver_role = action.get("approver_role")

                member = await self._resolve_member(org_id, approver_type, approver_id, approver_role)
                if member is None:
                    continue

                if action_type == "escalate" and member.supervisor_id is not None:
                    supervisor = await self.members.get_membership(member.supervisor_id)
                    if supervisor is not None and supervisor.is_active:
                        member = supervisor

                step_name = action.get("step_name") or (
                    "Review requested" if action_type == "request_review" else rule.step_name
                )

                chain = await self._escalation_chain(org_id, member, amount, limit_field)
                for idx, step_member in enumerate(chain):
                    plan.append(PlannedStep(
                        step_number=step_number,
                        step_name=step_name if idx == 0 else f"{step_name} (escalated)",
                        approver_id=step_member.user_id, approver_role=step_member.role,
                        approver_group_id=None, spending_limit=getattr(step_member, limit_field),
                        auto_escalated=idx > 0 or action_type == "escalate",
                        metadata={"rule_id": str(rule.id), "action": action_type},
                    ))
                    step_number += 1
                continue

            # Unknown action type: skip it rather than fail the whole plan —
            # a rule authored for a newer engine version shouldn't break
            # routing for everyone else.

        return step_number

    # =========================================================
    # Rule matching
    # =========================================================

    @staticmethod
    def _matches(rule: ApprovalRule, context: dict[str, Any]) -> bool:

        if rule.conditions:
            try:
                return evaluate_conditions(rule.conditions, context)
            except ConditionError:
                import logging
                logging.getLogger(__name__).exception("Malformed conditions on approval rule %s — treating as no match.", rule.id)
                return False

        amount = context.get("amount")
        if rule.min_amount is not None and amount is not None and amount < rule.min_amount:
            return False
        if rule.max_amount is not None and amount is not None and amount > rule.max_amount:
            return False
        if rule.vendor_id is not None and str(rule.vendor_id) != str(context.get("vendor_id")):
            return False
        if rule.department is not None and (context.get("department") or "").lower() != rule.department.lower():
            return False
        if rule.cost_center is not None and (context.get("cost_center") or "").lower() != rule.cost_center.lower():
            return False
        if rule.location is not None and (context.get("location") or "").lower() != rule.location.lower():
            return False
        if rule.document_type is not None and (context.get("document_type") or "").lower() != rule.document_type.lower():
            return False
        if rule.risk_level is not None and (context.get("risk_level") or "").lower() != rule.risk_level.lower():
            return False
        requires_po = context.get("requires_po")
        if rule.requires_po is not None and requires_po is not None and rule.requires_po != requires_po:
            return False
        return True

    # =========================================================
    # Approver resolution
    # =========================================================

    async def _resolve_member(
        self, org_id: UUID, approver_type: ApproverType,
        approver_id: UUID | None, approver_role: str | None,
    ) -> OrganizationMember | None:

        if approver_type == ApproverType.USER:
            if approver_id is None:
                return None
            member = await self.members.get_org_member(org_id, approver_id)
            return member if member and member.is_active else None

        # ROLE
        if not approver_role:
            return None
        candidates = await self.members.list_role_members(org_id, OrgRole(approver_role))
        active = [m for m in candidates if m.is_active]
        return active[0] if active else None

    async def _escalation_chain(
        self,
        org_id: UUID,
        member: OrganizationMember,
        amount: Decimal,
        limit_field: str,
    ) -> list[OrganizationMember]:
        """
        Walks the supervisor_id chain while the current member's limit
        (bill or payment, per limit_field) is smaller than the document
        amount. A member with no configured limit is treated as having
        unrestricted authority — orgs that haven't set limits yet keep
        the pre-existing single-approver behaviour.
        """

        chain = [member]
        current = member
        seen = {str(member.id)}

        for _ in range(MAX_ESCALATION_DEPTH):
            limit = getattr(current, limit_field)
            if limit is None or amount <= limit:
                break
            if current.supervisor_id is None:
                break
            supervisor = await self.members.get_membership(current.supervisor_id)
            if supervisor is None or str(supervisor.id) in seen or not supervisor.is_active:
                break
            chain.append(supervisor)
            seen.add(str(supervisor.id))
            current = supervisor

        return chain

    # =========================================================
    # Legacy fallback (no rules configured yet)
    # =========================================================

    async def _legacy_fallback(
        self,
        org_id: UUID,
        amount: Decimal,
        scope: ApprovalRuleScope,
    ) -> tuple[list[PlannedStep], str]:

        rows = (
            self.db.table("org_members")
            .select("user_id,role,spending_limit,payment_approval_limit")
            .eq("org_id", str(org_id))
            .eq("is_active", True)
            .execute()
            .data or []
        )

        # Do not pass the role list to PostgREST: the deployed ``org_role``
        # enum may not contain every application role (finance_manager and
        # ap_manager are missing in some environments), and Postgres rejects
        # the whole query when one value is unknown. Filtering here also keeps
        # the fallback working across schema versions.
        rows = [row for row in rows if row.get("role") in LEGACY_ROLE_ORDER]

        if not rows:
            return [], "sequential"

        rank = {role: index for index, role in enumerate(LEGACY_ROLE_ORDER)}
        rows.sort(key=lambda row: rank.get(row.get("role"), 999))
        row = rows[0]
        limit = row.get("payment_approval_limit") if scope == ApprovalRuleScope.PAYMENT else row.get("spending_limit")

        return [
            PlannedStep(
                step_number=1,
                step_name="AP Approval",
                approver_id=UUID(row["user_id"]),
                approver_role=row["role"],
                approver_group_id=None,
                spending_limit=limit,
                metadata={"fallback": True},
            )
        ], "sequential"
