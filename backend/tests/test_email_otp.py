"""Ticket 7 — registration, six-digit email OTP, and verification gate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.auth import SignUpRequest
from app.services.auth.verification_service import (
    EmailVerificationService,
    hash_code,
    resolve_email_verified,
)

ORG_ID = UUID("00000000-0000-0000-0000-0000000000e1")


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now = self.now + timedelta(**kwargs)


class FakeSender:
    def __init__(self) -> None:
        self.codes: list[str] = []

    async def send_code(self, *, user_id, email, code, first_name=None) -> bool:
        self.codes.append(code)
        return True


class FailingSender(FakeSender):
    async def send_code(self, *, user_id, email, code, first_name=None) -> bool:
        self.codes.append(code)
        return False


class FakeAuthRepository:
    def __init__(self) -> None:
        self.confirmed: list[str] = []
        self.fail = False

    async def admin_confirm_email(self, user_id) -> None:
        if self.fail:
            raise RuntimeError("provider unavailable")
        self.confirmed.append(str(user_id))


@pytest.fixture
def challenge_env(fake_db):
    sender = FakeSender()
    auth = FakeAuthRepository()
    clock = Clock()
    service = EmailVerificationService(
        repository=__import__(
            "app.repositories.auth.verification_repository",
            fromlist=["EmailVerificationRepository"],
        ).EmailVerificationRepository(db=fake_db),
        sender=sender,
        auth_repository=auth,
        now=clock,
    )
    return SimpleNamespace(
        service=service,
        sender=sender,
        auth=auth,
        clock=clock,
        db=fake_db,
        user_id=uuid4(),
        email="owner@example.com",
    )


async def _issue(env) -> None:
    await env.service.issue(
        user_id=env.user_id,
        email=env.email,
        first_name="Ada",
    )


# ---------------------------------------------------------------------------
# Code storage and issue
# ---------------------------------------------------------------------------


async def test_issue_stores_only_a_hash_and_hides_code_from_logs(challenge_env):
    env = challenge_env
    await _issue(env)

    code = env.sender.codes[-1]
    assert len(code) == 6 and code.isdigit()

    rows = env.db.tables["auth_email_verifications"]
    assert len(rows) == 1
    row = rows[0]

    assert row["code_hash"] != code
    assert code not in str(row)
    assert row["code_hash"] == hash_code(email=env.email, code=code)
    assert row["status"] == "pending"
    assert row["attempts"] == 0
    assert row["max_attempts"] == 5

    expires = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
    assert expires - env.clock.now == timedelta(minutes=10)


async def test_email_send_failure_does_not_leak_the_code(challenge_env, monkeypatch):
    env = challenge_env
    env.service.sender = FailingSender()

    events: list[str] = []
    monkeypatch.setattr(
        "app.services.auth.verification_service.logger.exception",
        lambda *args, **kwargs: events.append(str(args)),
    )

    result = await env.service.issue(
        user_id=env.user_id,
        email=env.email,
    )

    assert result["code_sent"] is False
    assert env.service.sender.codes
    assert env.service.sender.codes[0] not in " ".join(events)


# ---------------------------------------------------------------------------
# Verify: wrong, locked, expired, single-use
# ---------------------------------------------------------------------------


async def test_wrong_code_counts_attempts_and_locks(challenge_env):
    env = challenge_env
    await _issue(env)
    code = env.sender.codes[-1]

    for expected_remaining in (4, 3, 2, 1):
        result = await env.service.verify(
            email=env.email, code="000000" if code != "000000" else "111111"
        )
        assert result.status == "invalid"
        assert result.attempts_remaining == expected_remaining

    locked = await env.service.verify(
        email=env.email, code="000000" if code != "000000" else "111111"
    )
    assert locked.status == "locked"

    # The correct code cannot revive a locked challenge.
    rejected = await env.service.verify(email=env.email, code=code)
    assert rejected.status == "locked"
    assert env.auth.confirmed == []
    assert env.db.tables["auth_email_verifications"][0]["status"] == "locked"


async def test_expired_code_is_rejected_and_marked_expired(challenge_env):
    env = challenge_env
    await _issue(env)
    code = env.sender.codes[-1]

    env.clock.advance(minutes=11)

    result = await env.service.verify(email=env.email, code=code)

    assert result.status == "expired"
    assert env.db.tables["auth_email_verifications"][0]["status"] == "expired"
    assert env.auth.confirmed == []


async def test_valid_code_is_single_use_and_confirms_the_provider(challenge_env):
    env = challenge_env
    await _issue(env)
    code = env.sender.codes[-1]

    first = await env.service.verify(email=env.email, code=code)

    assert first.status == "verified"
    assert env.auth.confirmed == [str(env.user_id)]
    assert env.db.tables["auth_email_verifications"][0]["status"] == "verified"

    second = await env.service.verify(email=env.email, code=code)
    assert second.status == "already_verified"


async def test_provider_confirmation_failure_keeps_code_usable(challenge_env):
    env = challenge_env
    await _issue(env)
    code = env.sender.codes[-1]
    env.auth.fail = True

    failed = await env.service.verify(email=env.email, code=code)
    assert failed.status == "delivery_failed"
    assert env.db.tables["auth_email_verifications"][0]["status"] == "pending"

    env.auth.fail = False
    retried = await env.service.verify(email=env.email, code=code)
    assert retried.status == "verified"


# ---------------------------------------------------------------------------
# Resend: cooldown, rate limit, new code invalidates old
# ---------------------------------------------------------------------------


async def test_resend_respects_cooldown_then_invalidates_the_old_code(challenge_env):
    env = challenge_env
    await _issue(env)
    old_code = env.sender.codes[-1]

    blocked = await env.service.resend(email=env.email)
    assert blocked["code_sent"] is False
    assert blocked["retry_after_seconds"] > 0

    env.clock.advance(seconds=61)
    sent = await env.service.resend(email=env.email)

    assert sent["code_sent"] is True
    new_code = env.sender.codes[-1]
    assert new_code != old_code

    old_result = await env.service.verify(email=env.email, code=old_code)
    assert old_result.status in {"invalid", "expired"}

    new_result = await env.service.verify(email=env.email, code=new_code)
    assert new_result.status == "verified"


async def test_resend_never_reopens_a_verified_email(challenge_env):
    env = challenge_env
    await _issue(env)
    await env.service.verify(email=env.email, code=env.sender.codes[-1])

    env.clock.advance(seconds=61)
    result = await env.service.resend(email=env.email)

    assert result["code_sent"] is False
    assert len(env.db.tables["auth_email_verifications"]) == 1
    assert env.db.tables["auth_email_verifications"][0]["status"] == "verified"


async def test_resend_unknown_email_is_non_enumerating(challenge_env):
    env = challenge_env

    result = await env.service.resend(email="nobody@example.com")

    assert result["message"] == (
        "If an account is waiting for verification, a new six-digit code has "
        "been sent."
    )
    assert result["code_sent"] is False
    assert result["retry_after_seconds"] is None


# ---------------------------------------------------------------------------
# Schema: required fields, optional mobile, no commercial identifiers
# ---------------------------------------------------------------------------


def test_registration_requires_names_and_allows_optional_mobile():
    request = SignUpRequest(
        first_name="  Ada ",
        last_name="Lovelace",
        email="ada@example.co.uk",
        password="a-secure-password",
        mobile="+234 801 234 5678",
    )

    assert request.first_name == "Ada"
    assert request.mobile == "+2348012345678"

    fields = set(SignUpRequest.model_fields)
    assert {"first_name", "last_name", "email", "password", "mobile"} <= fields
    assert not (fields & {"company_number", "tax_id", "card", "referral_code"})


def test_registration_rejects_missing_names_and_bad_mobile():
    with pytest.raises(ValidationError):
        SignUpRequest(
            last_name="Lovelace",
            email="ada@example.com",
            password="a-secure-password",
        )

    with pytest.raises(ValidationError):
        SignUpRequest(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            password="a-secure-password",
            mobile="08012345678",
        )


# ---------------------------------------------------------------------------
# Verification gate
# ---------------------------------------------------------------------------


async def test_require_verified_user_denies_an_unverified_account():
    from fastapi import HTTPException

    from app.context import AuthUser
    from app.core.auth import require_verified_user

    unverified = AuthUser(
        id=uuid4(),
        email="pending@example.com",
        is_verified=False,
    )

    with pytest.raises(HTTPException) as excinfo:
        await require_verified_user(user=unverified)

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail["code"] == "EMAIL_VERIFICATION_REQUIRED"


async def test_require_verified_user_allows_a_verified_account():
    from app.context import AuthUser
    from app.core.auth import require_verified_user

    verified = AuthUser(
        id=uuid4(),
        email="verified@example.com",
        is_verified=True,
    )

    assert await require_verified_user(user=verified) is verified


@pytest.fixture
def unverified_client(fake_db, monkeypatch):
    import app.routers.documents as documents_router
    from app.context import AuthUser, OrganizationContext
    from app.core.auth import get_current_user
    from app.core.enum.database import OrgRole, PlanType
    from app.core.ocm import get_org_context
    from app.core.permissions import VIEW_DOCUMENTS
    from app.main import app

    user = AuthUser(
        id=uuid4(),
        email="pending@example.com",
        org_id=ORG_ID,
        role=OrgRole.OWNER,
        is_verified=False,
    )
    context = OrganizationContext(
        user_id=str(user.id),
        org_id=ORG_ID,
        name="Pending Org",
        slug="pending-org",
        plan=PlanType.FREE,
        role=OrgRole.OWNER,
        permissions={VIEW_DOCUMENTS},
        document_limit=100,
        default_currency="GBP",
        timezone="Europe/London",
    )

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_org_context] = lambda: context
    monkeypatch.setattr(documents_router, "get_supabase", lambda: fake_db)

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_unverified_user_is_denied_on_a_protected_router(unverified_client):
    response = unverified_client.get("/api/v2/documents")

    assert response.status_code == 403
    assert "EMAIL_VERIFICATION_REQUIRED" in response.text
    assert "six-digit" in response.text


class FakeAuthService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.user_id = uuid4()

    async def signup(self, email, password, metadata=None):
        self.calls.append((str(email), password, metadata or {}))
        return SimpleNamespace(
            user=SimpleNamespace(
                id=self.user_id,
                email=str(email),
                email_confirmed_at=None,
            ),
            session=None,
        )


class FakeVerificationService:
    def __init__(self) -> None:
        self.issued: list[dict] = []

    async def issue(self, *, user_id, email, first_name=None):
        self.issued.append(
            {
                "user_id": str(user_id),
                "email": email,
                "first_name": first_name,
            }
        )
        return {
            "code_sent": True,
            "expires_in_seconds": 600,
            "resend_cooldown_seconds": 60,
        }


def test_signup_creates_verification_and_never_issues_a_session(client, monkeypatch):
    from app.core.container import get_container

    auth = FakeAuthService()
    verifications = FakeVerificationService()
    container = get_container()
    monkeypatch.setattr(container, "auth_service", auth, raising=False)
    monkeypatch.setattr(
        container,
        "email_verification_service",
        verifications,
        raising=False,
    )

    response = client.post(
        "/api/v2/auth/signup",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.co.uk",
            "password": "a-secure-password",
            "mobile": "+2348012345678",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["requires_email_verification"] is True
    assert body["verification_email_sent"] is True
    assert body["access_token"] is None
    assert "access_token" not in response.cookies

    assert auth.calls[0][2] == {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "mobile": "+2348012345678",
    }
    assert verifications.issued[0]["first_name"] == "Ada"
    # Email verification is sufficient: no SMS step is required for a
    # Nigerian mobile number or any other optional mobile value.
    assert verifications.issued[0]["email"] == "ada@example.co.uk"


def test_resolve_email_verified_handles_legacy_and_otp_rows(monkeypatch):
    from app.services.auth import verification_service

    class Repo:
        status = None

        def latest_status_for_user_sync(self, _user_id):
            return self.status

    repo = Repo()
    monkeypatch.setattr(
        verification_service,
        "EmailVerificationRepository",
        lambda: repo,
    )

    # Supabase unconfirmed is always unverified.
    assert resolve_email_verified(uuid4(), supabase_verified=False) is False

    # No OTP row: legacy account trusts Supabase confirmation.
    assert resolve_email_verified(uuid4(), supabase_verified=True) is True

    repo.status = "pending"
    assert resolve_email_verified(uuid4(), supabase_verified=True) is False

    repo.status = "verified"
    assert resolve_email_verified(uuid4(), supabase_verified=True) is True
