from __future__ import annotations
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID
from app.repositories.approval.authority_repository import ApprovalAuthorityRepository
from app.repositories.approval.delegation_repository import ApprovalDelegationRepository

class ApprovalAuthorityService:
    def __init__(self, authorities=None, delegations=None):
        self.authorities = authorities or ApprovalAuthorityRepository()
        self.delegations = delegations or ApprovalDelegationRepository()

    async def can_approve(self, *, org_id: UUID, membership_id: UUID, approval_type: str, currency: str, amount: Decimal, self_approval: bool = False):
        authority = await self.authorities.active_for_member(org_id, membership_id, approval_type, currency, amount)
        if authority is None: return False
        if self_approval and not authority.get("can_self_approve", False): return False
        return True

    async def effective_approver(self, *, org_id: UUID, membership_id: UUID, approval_type: str, currency: str, amount: Decimal):
        if await self.can_approve(org_id=org_id, membership_id=membership_id, approval_type=approval_type, currency=currency, amount=amount):
            return membership_id
        for row in await self.delegations.list_active(org_id):
            scope = row.get("scope") or {}
            if row.get("delegator_membership_id") == str(membership_id) and scope.get(approval_type, False):
                delegatee = UUID(row["delegatee_membership_id"])
                if await self.can_approve(org_id=org_id, membership_id=delegatee, approval_type=approval_type, currency=currency, amount=amount):
                    return delegatee
        return None
