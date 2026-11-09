from uuid import UUID
from app.core.enum.ap import ApprovalRuleScope, ApproverType
from app.models.domain.ap import ApprovalRule
from app.repositories.ap.rules_repository import ApprovalRuleRepository
from app.services.ap.condition_evaluator import ConditionError, validate as validate_conditions

_VALID_ACTION_TYPES = {
    "add_approver", "require_approver", "route_to_group", "escalate",
    "block", "auto_approve", "auto_reject", "request_review",
}
_TERMINAL_ACTION_TYPES = {"block", "auto_approve", "auto_reject"}


class ApprovalRuleService:
    """
    Application service for the AP routing/approval rules engine.

    Creates go through plain dicts, not a fully-populated ApprovalRule
    instance — id/created_at/updated_at are Postgres-generated
    (gen_random_uuid()/now()) and come back on the insert response,
    which the repository then maps into the domain model for the
    return value.

    Validation here mirrors both the DB check constraint
    (chk_ap_rule_approver, for the legacy single-approver fields) and
    the newer, optional conditions/actions JSONB fields, so a bad
    rule is rejected with a clear message before it ever reaches
    Postgres — or worse, silently fails to match/act at routing time.
    """

    def __init__(self, repository: ApprovalRuleRepository | None = None) -> None:
        self.repository = repository or ApprovalRuleRepository()

    @staticmethod
    def _validate_approver(data: dict) -> None:
        # A rule with `actions` carries its own per-action approver
        # info and doesn't use the single approver_type/id/role/group
        # fields at all — the DB check constraint still applies to
        # those columns, but they're simply left at their defaults
        # (approver_type='role' with no approver_role) when actions
        # are used, so skip this stricter application-level check.
        if data.get("actions"):
            return
        approver_type = data.get("approver_type")
        if approver_type == ApproverType.USER.value and not data.get("approver_id"):
            raise ValueError("A user-type rule requires approver_id.")
        if approver_type == ApproverType.ROLE.value and not data.get("approver_role"):
            raise ValueError("A role-type rule requires approver_role.")
        if approver_type == ApproverType.GROUP.value and not data.get("approver_group_id"):
            raise ValueError("A group-type rule requires approver_group_id.")

    @staticmethod
    def _validate_conditions(data: dict) -> None:
        conditions = data.get("conditions")
        if not conditions:
            return
        try:
            validate_conditions(conditions)
        except ConditionError as exc:
            raise ValueError(f"Invalid conditions: {exc}") from exc

    @staticmethod
    def _validate_actions(data: dict) -> None:
        actions = data.get("actions")
        if not actions:
            return
        if not isinstance(actions, list):
            raise ValueError("actions must be a list.")

        terminal_count = 0
        for i, action in enumerate(actions):
            if not isinstance(action, dict) or "type" not in action:
                raise ValueError(f"actions[{i}] must be an object with a 'type' field.")
            action_type = action["type"]
            if action_type not in _VALID_ACTION_TYPES:
                raise ValueError(f"actions[{i}].type {action_type!r} is not one of {sorted(_VALID_ACTION_TYPES)}.")
            if action_type in _TERMINAL_ACTION_TYPES:
                terminal_count += 1
            if action_type == "route_to_group" and not action.get("approver_group_id"):
                raise ValueError(f"actions[{i}] (route_to_group) requires approver_group_id.")
            if action_type in ("add_approver", "require_approver", "escalate"):
                a_type = action.get("approver_type", "role")
                if a_type == "user" and not action.get("approver_id"):
                    raise ValueError(f"actions[{i}] ({action_type}, approver_type=user) requires approver_id.")
                if a_type == "role" and not action.get("approver_role"):
                    raise ValueError(f"actions[{i}] ({action_type}, approver_type=role) requires approver_role.")

        if terminal_count > 1:
            raise ValueError("A rule's actions may include at most one terminal action (block/auto_approve/auto_reject).")
        if terminal_count == 1 and len(actions) > 1:
            raise ValueError("A terminal action (block/auto_approve/auto_reject) must be the rule's only action.")

    async def list_rules(self, org_id: UUID, scope: ApprovalRuleScope | None = None) -> list[ApprovalRule]:
        rows = await self.repository.list(
            org_id,
            scope=scope.value if scope is not None else None,
            active_only=True,
        )
        return [
            row if isinstance(row, ApprovalRule) else ApprovalRule.model_validate(row)
            for row in rows
        ]

    async def create_rule(self, org_id: UUID, data: dict, created_by: UUID) -> ApprovalRule:
        self._validate_approver(data)
        self._validate_conditions(data)
        self._validate_actions(data)
        payload = {**data, "created_by": str(created_by)}
        created = await self.repository.create(org_id, payload)
        if created is None:
            raise RuntimeError("Failed to create approval rule.")
        return created if isinstance(created, ApprovalRule) else ApprovalRule.model_validate(created)

    async def update_rule(self, org_id: UUID, rule_id: UUID, data: dict) -> ApprovalRule:
        existing = await self.repository.get(org_id, rule_id)
        if existing is None:
            raise ValueError("Approval rule not found.")

        existing_data = existing if isinstance(existing, dict) else existing.model_dump(mode="python")
        merged = dict(existing_data)
        merged.update(data)
        self._validate_approver(merged)
        self._validate_conditions(merged)
        self._validate_actions(merged)

        updated = await self.repository.update(org_id, rule_id, data)
        if updated is None:
            raise RuntimeError(f"Failed to update approval rule {rule_id}.")
        return updated if isinstance(updated, ApprovalRule) else ApprovalRule.model_validate(updated)

    async def delete_rule(self, org_id: UUID, rule_id: UUID) -> bool:
        existing = await self.repository.get(org_id, rule_id)
        if existing is None:
            raise ValueError("Approval rule not found.")
        return await self.repository.delete(org_id, rule_id)
