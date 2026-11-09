import pytest
from pydantic import ValidationError
from datetime import datetime, UTC
from types import SimpleNamespace
from uuid import uuid4

from app.context.auth import AuthUser
from app.schemas.onboarding import OnboardingComplete, OnboardingDraftUpdate


def valid_onboarding_data():
    return {
        "name": "Northstar Studio",
        "country": "GB",
        "currency": "GBP",
        "business_type": "not_registered",
        "industry": "consulting",
        "company_size": "2-10",
        "monthly_invoice_volume": "11-25",
        "accounting_software": "none",
    }


def test_onboarding_accepts_unregistered_manual_business():
    onboarding = OnboardingComplete(**valid_onboarding_data())

    assert onboarding.business_type == "not_registered"
    assert onboarding.accounting_software == "none"
    assert onboarding.invite_emails == []


def test_onboarding_rejects_unsupported_accounting_choice():
    with pytest.raises(ValidationError):
        OnboardingComplete(**{**valid_onboarding_data(), "accounting_software": "freshbooks"})


def test_draft_step_is_bounded():
    with pytest.raises(ValidationError):
        OnboardingDraftUpdate(step=7, data={})


@pytest.mark.asyncio
async def test_onboarding_invite_preview_is_saved_without_sending_invites(monkeypatch):
    for key, value in {
        "SECRET_KEY": "test-secret-key-for-unit-tests-only",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_KEY": "test-service-key",
        "STRIPE_SECRET_KEY": "sk_test_placeholder",
        "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
    }.items():
        monkeypatch.setenv(key, value)
    from app.schemas.workspace import WorkspaceSummary
    from app.services.organization_service import OrganizationService

    user_id, workspace_id = uuid4(), uuid4()
    saved = {}

    class Drafts:
        def get(self, requested_user_id):
            return None

        def save(self, requested_user_id, *, step, data):
            saved.update(data)
            return {}

        def claim_workspace_id(self, requested_user_id):
            return workspace_id

        def mark_completed(self, requested_user_id, requested_workspace_id):
            assert requested_workspace_id == workspace_id

    service = OrganizationService.__new__(OrganizationService)
    service.onboarding_drafts = Drafts()

    async def create_workspace(**kwargs):
        assert kwargs["workspace_id"] == workspace_id
        return WorkspaceSummary(
            id=workspace_id, name="Northstar Studio", slug="northstar", type="business",
            role="owner", plan="free", currency="GBP", created_at=datetime.now(UTC),
        )

    service.create_workspace = create_workspace
    data = OnboardingComplete(**{
        **valid_onboarding_data(),
        "invite_emails": ["teammate@example.test"],
        "approver_email": "approver@example.test",
    })

    await service.complete_onboarding(user=AuthUser(id=user_id, email="owner@example.test"), data=data)

    assert saved["invite_emails"] == ["teammate@example.test"]
    assert saved["approver_email"] == "approver@example.test"


@pytest.mark.asyncio
async def test_completed_onboarding_retry_returns_the_original_workspace(monkeypatch):
    # Constructing the service imports its repository graph, which loads
    # settings. Dummy local values keep this unit test independent of secrets.
    for key, value in {
        "SECRET_KEY": "test-secret-key-for-unit-tests-only",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_KEY": "test-service-key",
        "STRIPE_SECRET_KEY": "sk_test_placeholder",
        "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
    }.items():
        monkeypatch.setenv(key, value)
    from app.services.organization_service import OrganizationService

    user_id, workspace_id = uuid4(), uuid4()
    organization = SimpleNamespace(
        id=workspace_id, name="Northstar Studio", slug="northstar", created_by=user_id,
        plan="free", currency="GBP", created_at=datetime.now(UTC),
    )

    class Drafts:
        def get(self, requested_user_id):
            return {"completed": True, "workspace_id": str(workspace_id)}

        def claim_workspace_id(self, requested_user_id):
            raise AssertionError("a completed onboarding must not claim another workspace")

    class Organizations:
        async def get_organization(self, requested_id):
            assert requested_id == workspace_id
            return organization

    class Members:
        async def get_org_member(self, requested_org_id, requested_user_id):
            return SimpleNamespace(is_active=True, role="owner")

    service = OrganizationService.__new__(OrganizationService)
    service.onboarding_drafts = Drafts()
    service.organizations = Organizations()
    service.members = Members()

    result = await service.complete_onboarding(
        user=AuthUser(id=user_id, email="owner@example.test"),
        data=OnboardingComplete(**valid_onboarding_data()),
    )

    assert result.id == workspace_id
    assert result.currency == "GBP"


@pytest.mark.asyncio
async def test_retrying_reserved_workspace_does_not_duplicate_owner_membership(monkeypatch):
    for key, value in {
        "SECRET_KEY": "test-secret-key-for-unit-tests-only",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_KEY": "test-service-key",
        "STRIPE_SECRET_KEY": "sk_test_placeholder",
        "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
    }.items():
        monkeypatch.setenv(key, value)
    from app.core.enum.database import OrgRole, PlanType
    from app.services.organization_service import OrganizationService

    user_id, workspace_id = uuid4(), uuid4()

    class Organizations:
        org = None
        creates = 0

        async def get_organization(self, requested_id):
            return self.org if self.org and requested_id == workspace_id else None

        async def create_organization(self, payload):
            self.creates += 1
            self.org = SimpleNamespace(
                id=payload["id"], name=payload["name"], slug=payload["slug"],
                plan=PlanType.FREE, currency=payload["currency"], created_at=datetime.now(UTC),
                created_by=user_id,
            )
            return self.org

        async def delete_organization(self, requested_id):
            self.org = None

    class Members:
        membership = None
        creates = 0

        async def get_org_member(self, org_id, requested_user_id):
            return self.membership

        async def create_membership(self, payload):
            self.creates += 1
            self.membership = SimpleNamespace(id=uuid4(), role=OrgRole.OWNER, is_active=True)
            return self.membership

        async def list_organization_members(self, org_id):
            return [self.membership] if self.membership else []

        async def delete_membership(self, membership_id):
            self.membership = None

    class Settings:
        created = False

        async def settings_exist(self, org_id):
            return self.created

        async def create_settings(self, payload):
            self.created = True

    class Usage:
        created = False

        def current_month(self):
            return "2026-11-01"

        async def usage_exists(self, org_id, month):
            return self.created

        async def create_usage(self, payload):
            self.created = True

    service = OrganizationService.__new__(OrganizationService)
    service.organizations, service.members = Organizations(), Members()
    service.settings, service.usage = Settings(), Usage()
    user = AuthUser(id=user_id, email="owner@example.test")
    args = dict(user=user, workspace_type="business", name="Northstar Studio", currency="GBP", country="GB", workspace_id=workspace_id)

    first = await service.create_workspace(**args)
    second = await service.create_workspace(**args)

    assert first.id == second.id == workspace_id
    assert service.organizations.creates == 1
    assert service.members.creates == 1


@pytest.mark.asyncio
async def test_retry_does_not_promote_an_existing_non_owner_membership(monkeypatch):
    for key, value in {
        "SECRET_KEY": "test-secret-key-for-unit-tests-only",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_KEY": "test-service-key",
        "STRIPE_SECRET_KEY": "sk_test_placeholder",
        "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
    }.items():
        monkeypatch.setenv(key, value)
    from fastapi import HTTPException
    from app.core.enum.database import OrgRole
    from app.services.organization_service import OrganizationService

    user_id, workspace_id = uuid4(), uuid4()
    organization = SimpleNamespace(created_by=user_id)
    member = SimpleNamespace(id=uuid4(), role=OrgRole.MEMBER, is_active=True)

    class Organizations:
        async def get_organization(self, requested_id):
            return organization

    class Members:
        updates = 0

        async def get_org_member(self, org_id, requested_user_id):
            return member

        async def update_membership(self, membership_id, data):
            self.updates += 1

    service = OrganizationService.__new__(OrganizationService)
    service.organizations, service.members = Organizations(), Members()

    with pytest.raises(HTTPException) as raised:
        await service.create_workspace(
            user=AuthUser(id=user_id, email="owner@example.test"),
            workspace_type="business", name="Northstar Studio", currency="GBP", country="GB",
            workspace_id=workspace_id,
        )

    assert raised.value.status_code == 403
    assert service.members.updates == 0


def test_draft_repository_reads_only_the_authenticated_users_row(monkeypatch):
    for key, value in {
        "SECRET_KEY": "test-secret-key-for-unit-tests-only",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_KEY": "test-service-key",
        "STRIPE_SECRET_KEY": "sk_test_placeholder",
        "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
    }.items():
        monkeypatch.setenv(key, value)
    from app.repositories.organization.onboarding_draft_repository import OnboardingDraftRepository

    user_id = uuid4()

    class Query:
        def __init__(self):
            self.filters = []

        def select(self, columns):
            return self

        def eq(self, key, value):
            self.filters.append((key, value))
            return self

        def limit(self, count):
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    class Database:
        query = Query()

        def table(self, name):
            assert name == "onboarding_drafts"
            return self.query

    repository = OnboardingDraftRepository.__new__(OnboardingDraftRepository)
    repository.db = Database()

    assert repository.get(user_id) is None
    assert ("user_id", str(user_id)) in repository.db.query.filters
