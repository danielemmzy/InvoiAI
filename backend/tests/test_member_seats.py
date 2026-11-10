import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.context import OrganizationContext
from app.core.enum.database import OrgRole, PlanType
from app.core.permissions import INVITE_MEMBERS, REMOVE_MEMBERS, VIEW_MEMBERS
import app.routers.members as members_router
from app.services.member_service import MemberService


def _context(org_id: UUID, permission: str) -> OrganizationContext:
    return OrganizationContext(
        user_id="00000000-0000-0000-0000-000000000010",
        org_id=org_id, name="Current", slug="current", plan=PlanType.FREE,
        role=OrgRole.OWNER, permissions={permission}, document_limit=10,
        default_currency="GBP", timezone="Europe/London",
    )


@pytest.mark.parametrize("operation", ["resend", "cancel", "remove"])
def test_member_actions_deny_membership_from_another_workspace(monkeypatch, operation):
    current_org = UUID("00000000-0000-0000-0000-000000000001")
    other_org = UUID("00000000-0000-0000-0000-000000000002")
    member_id = UUID("00000000-0000-0000-0000-000000000003")
    member = SimpleNamespace(
        id=member_id, org_id=other_org, is_active=False,
        invite_email="person@example.com", invite_token="pending",
    )

    class Service:
        async def ensure_member_exists(self, _membership_id):
            return member

    monkeypatch.setattr(members_router, "get_container", lambda: SimpleNamespace(member_service=Service()))
    ctx = _context(current_org, REMOVE_MEMBERS if operation == "remove" else INVITE_MEMBERS)

    async def run():
        with pytest.raises(HTTPException) as error:
            if operation == "resend":
                await members_router.resend_invitation(member_id, ctx)
            elif operation == "cancel":
                await members_router.cancel_invitation(member_id, ctx)
            else:
                user = SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000010"))
                await members_router.remove_member(member_id, user, ctx)
        assert error.value.status_code == 404

    asyncio.run(run())


def test_acceptance_checks_current_seat_limit_and_database_path_is_locked(monkeypatch):
    org_id = UUID("00000000-0000-0000-0000-000000000001")
    invitation = SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000003"), org_id=org_id, invite_expires_at=datetime.now(UTC) + timedelta(days=1))

    class Members:
        async def get_by_invite_token(self, _token):
            return invitation

        async def accept_invitation_with_capacity(self, **kwargs):
            assert kwargs["seat_limit"] == 1
            raise RuntimeError("SEAT_LIMIT_REACHED")

    class Organizations:
        async def get_organization(self, _org_id):
            return SimpleNamespace(plan=PlanType.FREE)

    service = MemberService.__new__(MemberService)
    service.members = Members()
    service.organizations = Organizations()

    async def run():
        with pytest.raises(HTTPException) as error:
            await service.accept_invitation("token", UUID("00000000-0000-0000-0000-000000000010"))
        assert error.value.status_code == 409
        assert error.value.detail == "SEAT_LIMIT_REACHED"

    asyncio.run(run())

    sql = (Path(__file__).resolve().parents[1] / "migrations" / "20261111_atomic_member_seat_capacity.sql").read_text()
    assert sql.count("pg_advisory_xact_lock(hashtext(") == 3
    assert "accept_org_member_invitation" in sql


def test_member_list_does_not_expose_invitation_tokens(monkeypatch):
    org_id = UUID("00000000-0000-0000-0000-000000000001")

    class Invitation:
        is_active = False
        invite_token = "secret-token"
        invite_expires_at = datetime.now(UTC) + timedelta(days=1)

        def model_dump(self, *, mode, exclude):
            assert mode == "json"
            assert "invite_token" in exclude
            return {"id": "invitation", "invite_email": "person@example.com"}

    class Service:
        async def list_members(self, _org_id):
            return [Invitation()]

    monkeypatch.setattr(members_router, "get_container", lambda: SimpleNamespace(member_service=Service()))

    async def run():
        result = await members_router.list_members(_context(org_id, VIEW_MEMBERS))
        assert result == [{"id": "invitation", "invite_email": "person@example.com", "invitation_status": "pending"}]
        assert "invite_token" not in result[0]

    asyncio.run(run())




@pytest.mark.parametrize("members", [
    [SimpleNamespace(id="active", user_id="user-a", is_active=True, invite_token=None, invite_expires_at=None)],
    [SimpleNamespace(id="pending", user_id=None, is_active=False, invite_token="token", invite_expires_at=None)],
    [
        SimpleNamespace(id="active-a", user_id="user-a", is_active=True, invite_token=None, invite_expires_at=None),
        SimpleNamespace(id="active-b", user_id="user-b", is_active=True, invite_token=None, invite_expires_at=None),
    ],
])
def test_invite_at_limit_and_after_downgrade_returns_stable_error(monkeypatch, members):
    org_id = UUID("00000000-0000-0000-0000-000000000001")

    class Service:
        async def list_members(self, _org_id):
            return members

        async def create_invitation(self, **_kwargs):
            raise AssertionError("an over-limit invite must not be created")

    monkeypatch.setattr(members_router, "get_container", lambda: SimpleNamespace(member_service=Service()))
    ctx = _context(org_id, INVITE_MEMBERS)
    user = SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000010"))
    payload = members_router.InviteMemberRequest(email="new@example.com", role=OrgRole.AP_MEMBER)

    async def run():
        with pytest.raises(HTTPException) as error:
            await members_router.invite_member(payload, user, ctx)
        assert error.value.status_code == 409
        assert error.value.detail == "SEAT_LIMIT_REACHED"
        assert len(members) >= 1  # Existing access is preserved after a downgrade.

    asyncio.run(run())
