from uuid import UUID

from app.core.enum.database import ApprovalDecision
from app.models.domain.approval import ApprovalStep
from app.repositories.ap.groups_repository import (
    ApprovalGroupMemberRepository,
    ApprovalGroupRepository,
)
from app.repositories.approval.step_repository import ApprovalStepRepository


class ApprovalGroupService:
    """
    CRUD for approval groups/membership, plus the "first to act
    claims it" semantics the video calls a processing group: any
    member of the group assigned to a step can claim it, which
    assigns them as the individual approver so the normal
    approve/reject flow (approvals router -> ApprovalEngine) then
    applies unchanged.
    """

    def __init__(
        self,
        groups: ApprovalGroupRepository | None = None,
        members: ApprovalGroupMemberRepository | None = None,
        steps: ApprovalStepRepository | None = None,
    ) -> None:
        self.groups = groups or ApprovalGroupRepository()
        self.members = members or ApprovalGroupMemberRepository()
        self.steps = steps or ApprovalStepRepository()

    # =========================================================
    # Groups
    # =========================================================

    async def list_groups(self, org_id: UUID):
        return await self.groups.list_groups(org_id)

    async def create_group(self, org_id: UUID, name: str, description: str | None, created_by: UUID):
        if not name or not name.strip():
            raise ValueError("Group name cannot be empty.")
        # id/created_at/updated_at are Postgres-generated; pass a dict
        # so the repository doesn't have to construct an under-populated
        # ApprovalGroup instance just to insert it.
        payload = {
            "org_id": str(org_id),
            "name": name.strip(),
            "description": description,
            "created_by": str(created_by),
        }
        created = await self.groups.create_group(payload)
        if created is None:
            raise RuntimeError("Failed to create approval group.")
        return created

    async def delete_group(self, org_id: UUID, group_id: UUID) -> bool:
        existing = await self.groups.get_group(group_id)
        if existing is None or str(existing.org_id) != str(org_id):
            raise ValueError("Approval group not found.")
        return await self.groups.delete_group(group_id)

    # =========================================================
    # Membership
    # =========================================================

    async def list_members(self, org_id: UUID, group_id: UUID):
        group = await self.groups.get_group(group_id)
        if group is None or str(group.org_id) != str(org_id):
            raise ValueError("Approval group not found.")
        return await self.members.list_members(group_id)

    async def add_member(self, org_id: UUID, group_id: UUID, user_id: UUID):
        group = await self.groups.get_group(group_id)
        if group is None or str(group.org_id) != str(org_id):
            raise ValueError("Approval group not found.")
        if await self.members.is_member(group_id, user_id):
            raise ValueError("User is already a member of this group.")
        return await self.members.add_member(group_id, user_id)

    async def remove_member(self, org_id: UUID, group_id: UUID, user_id: UUID) -> bool:
        group = await self.groups.get_group(group_id)
        if group is None or str(group.org_id) != str(org_id):
            raise ValueError("Approval group not found.")
        return await self.members.remove_member(group_id, user_id)

    # =========================================================
    # Claiming a pooled step
    # =========================================================

    async def claim_step(self, *, org_id: UUID, step_id: UUID, user_id: UUID) -> ApprovalStep:
        step = await self.steps.get_step(step_id)

        if step is None or str(step.org_id) != str(org_id):
            raise ValueError("Approval step not found.")

        if step.approver_group_id is None:
            raise ValueError("This step is not assigned to an approval group.")

        if step.decision != ApprovalDecision.PENDING:
            raise ValueError("Only pending steps can be claimed.")

        if step.claimed_by is not None:
            raise ValueError("This step has already been claimed by another approver.")

        if not await self.members.is_member(step.approver_group_id, user_id):
            raise ValueError("You are not a member of the approval group assigned to this step.")

        updated = await self.steps.claim_group_step(step_id, user_id)

        if updated is None:
            raise ValueError("This step was claimed by another approver before your claim was saved.")

        return updated
