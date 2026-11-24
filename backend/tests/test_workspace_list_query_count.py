"""The workspace switcher must not fetch organizations one membership at a time."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.enum.database import OrgRole, PlanType
from app.services.organization_service import OrganizationService


class Members:
    def __init__(self, count: int):
        self.memberships = [
            SimpleNamespace(
                org_id=uuid4(),
                is_active=True,
                role=OrgRole.OWNER.value,
            )
            for _ in range(count)
        ]

    async def list_user_memberships(self, _user_id):
        return self.memberships


class Organizations:
    def __init__(self):
        self.batch_calls = 0
        self.single_calls = 0

    def organizations_for(self, org_ids):
        return {
            str(org_id): SimpleNamespace(
                id=org_id,
                name=f"Workspace {index}",
                slug=f"workspace-{index}",
                features={},
                plan=PlanType.FREE.value,
                currency="GBP",
                created_at=datetime.now(UTC),
            )
            for index, org_id in enumerate(org_ids)
        }

    async def get_organizations_by_ids(self, org_ids):
        self.batch_calls += 1
        self.last_requested = org_ids
        return self.organizations_for(org_ids)

    async def get_organization(self, _org_id):  # pragma: no cover - regression path
        self.single_calls += 1
        raise AssertionError("workspace listing must not query organizations one by one")


@pytest.mark.parametrize("membership_count", [1, 8])
@pytest.mark.asyncio
async def test_list_user_workspaces_uses_one_organization_query(membership_count):
    service = object.__new__(OrganizationService)
    service.members = Members(membership_count)
    service.organizations = Organizations()

    workspaces = await service.list_user_workspaces(uuid4())

    assert len(workspaces) == membership_count
    assert service.organizations.batch_calls == 1
    assert service.organizations.single_calls == 0
    assert len(service.organizations.last_requested) == membership_count
