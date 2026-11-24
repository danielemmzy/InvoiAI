"""Login latency regressions: independent checks run concurrently and the
password grant's factor data removes a redundant auth-service round trip."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response

from app.repositories.auth.auth_repository import AuthRepository
from app.routers import auth_v2
from app.schemas.auth import AuthResponse, LoginRequest


def _auth_response() -> AuthResponse:
    return AuthResponse(
        access_token="access-token",
        refresh_token="refresh-token",
        user_id=str(uuid4()),
        email="owner@example.com",
        is_verified=True,
    )


def _supabase_result(*, factors=None, usable: bool = True):
    user = SimpleNamespace(
        id=uuid4(),
        email="owner@example.com",
        factors=factors,
        email_confirmed_at="2026-01-01T00:00:00Z",
    )
    session = SimpleNamespace(
        access_token="access-token",
        refresh_token="refresh-token",
    )
    return SimpleNamespace(
        user=user if usable else None,
        session=session if usable else None,
    )


def _patch_login(monkeypatch, result):
    class AuthService:
        async def login(self, email, password):
            return result

    monkeypatch.setattr(
        auth_v2,
        "get_container",
        lambda: SimpleNamespace(auth_service=AuthService()),
    )


async def _call_login():
    # Call the endpoint body directly; the route-level rate limiter is not
    # what these tests exercise.
    endpoint = getattr(auth_v2.login, "__wrapped__", auth_v2.login)
    return await endpoint(
        request=SimpleNamespace(),
        response=Response(),
        body=LoginRequest(email="owner@example.com", password="secret"),
    )


@pytest.mark.asyncio
async def test_verification_and_mfa_checks_run_concurrently(monkeypatch):
    events: list[tuple[str, str]] = []

    async def fake_response(_result):
        events.append(("start", "verification"))
        await asyncio.sleep(0.2)
        events.append(("end", "verification"))
        return _auth_response()

    async def fake_mfa(_user_id, _token, *, factors=None):
        events.append(("start", "mfa"))
        await asyncio.sleep(0.2)
        events.append(("end", "mfa"))
        return False, False

    _patch_login(monkeypatch, _supabase_result(factors=[]))
    monkeypatch.setattr(auth_v2, "_response", fake_response)
    monkeypatch.setattr(auth_v2, "_mfa_login_state", fake_mfa)
    monkeypatch.setattr(auth_v2, "_set_auth_cookies", lambda *args: None)

    started = time.perf_counter()
    await _call_login()
    elapsed = time.perf_counter() - started

    assert {name for phase, name in events if phase == "start"} == {
        "verification",
        "mfa",
    }
    # Both must start before either finishes, and the wall clock must be near
    # one check rather than the sum of both.
    assert events.index(("start", "mfa")) < events.index(("end", "verification"))
    assert events.index(("start", "verification")) < events.index(("end", "mfa"))
    assert elapsed < 0.35


@pytest.mark.asyncio
async def test_login_passes_password_grant_factors_to_the_mfa_gate(monkeypatch):
    factors = [SimpleNamespace(factor_type="totp", status="verified")]
    captured = {}

    async def fake_response(_result):
        return _auth_response()

    async def fake_mfa(user_id, access_token, *, factors=None):
        captured["user_id"] = user_id
        captured["access_token"] = access_token
        captured["factors"] = factors
        return False, True

    result = _supabase_result(factors=factors)
    _patch_login(monkeypatch, result)
    monkeypatch.setattr(auth_v2, "_response", fake_response)
    monkeypatch.setattr(auth_v2, "_mfa_login_state", fake_mfa)
    monkeypatch.setattr(auth_v2, "_set_auth_cookies", lambda *args: None)

    response = await _call_login()

    assert captured["user_id"] == str(result.user.id)
    assert captured["access_token"] == result.session.access_token
    assert captured["factors"] is factors
    assert response.mfa_challenge_required is True
    assert response.mfa_enrollment_required is False


@pytest.mark.asyncio
async def test_mfa_check_failure_returns_503_without_setting_cookies(monkeypatch):
    cookies = []

    async def fake_response(_result):
        return _auth_response()

    async def failing_mfa(_user_id, _token, *, factors=None):
        raise RuntimeError("membership backend unavailable")

    _patch_login(monkeypatch, _supabase_result())
    monkeypatch.setattr(auth_v2, "_response", fake_response)
    monkeypatch.setattr(auth_v2, "_mfa_login_state", failing_mfa)
    monkeypatch.setattr(auth_v2, "platform_error", lambda _exc: None)
    monkeypatch.setattr(
        auth_v2, "_set_auth_cookies", lambda *args: cookies.append(args)
    )

    with pytest.raises(HTTPException) as raised:
        await _call_login()

    assert raised.value.status_code == 503
    assert raised.value.detail["code"] == "MFA_STATUS_UNAVAILABLE"
    assert cookies == []


@pytest.mark.asyncio
async def test_unusable_auth_result_is_rejected_before_checks(monkeypatch):
    calls = []

    async def fake_response(_result):
        calls.append("verification")
        return _auth_response()

    _patch_login(monkeypatch, _supabase_result(usable=False))
    monkeypatch.setattr(auth_v2, "_response", fake_response)

    with pytest.raises(HTTPException) as raised:
        await _call_login()

    assert raised.value.status_code == 401
    assert calls == []


@pytest.mark.asyncio
async def test_verification_failure_is_not_masked_by_the_mfa_check(monkeypatch):
    cookies = []

    async def failing_response(_result):
        raise HTTPException(status_code=401, detail="Authentication failed")

    async def fake_mfa(_user_id, _token, *, factors=None):
        return False, False

    _patch_login(monkeypatch, _supabase_result())
    monkeypatch.setattr(auth_v2, "_response", failing_response)
    monkeypatch.setattr(auth_v2, "_mfa_login_state", fake_mfa)
    monkeypatch.setattr(
        auth_v2, "_set_auth_cookies", lambda *args: cookies.append(args)
    )

    with pytest.raises(HTTPException) as raised:
        await _call_login()

    assert raised.value.status_code == 401
    assert cookies == []


@pytest.mark.asyncio
async def test_mfa_gate_uses_supplied_factors_without_a_second_auth_call(
    monkeypatch,
):
    calls = []

    async def fake_run_db(fn, *args, **kwargs):
        calls.append(fn.__name__)
        return fn(*args, **kwargs)

    def has_admin_membership(_user_id):
        return True

    def factors_for_user(_token):
        raise AssertionError("must not re-fetch factors")

    monkeypatch.setattr(auth_v2, "run_db", fake_run_db)
    monkeypatch.setattr(
        auth_v2.mfa_service, "has_admin_membership", has_admin_membership
    )
    monkeypatch.setattr(auth_v2.mfa_service, "factors_for_user", factors_for_user)

    verified_totp = [SimpleNamespace(factor_type="totp", status="verified")]

    assert await auth_v2._mfa_login_state("user", "token", factors=verified_totp) == (
        False,
        True,
    )
    assert await auth_v2._mfa_login_state("user", "token", factors=[]) == (
        True,
        False,
    )
    assert calls == ["has_admin_membership", "has_admin_membership"]


@pytest.mark.asyncio
async def test_mfa_gate_falls_back_when_the_grant_omits_factors(monkeypatch):
    calls = []

    async def fake_run_db(fn, *args, **kwargs):
        calls.append(fn.__name__)
        return fn(*args, **kwargs)

    listed = SimpleNamespace(
        all=[SimpleNamespace(factor_type="totp", status="verified")]
    )

    def has_admin_membership(_user_id):
        return True

    def factors_for_user(_token):
        return listed

    monkeypatch.setattr(auth_v2, "run_db", fake_run_db)
    monkeypatch.setattr(
        auth_v2.mfa_service, "has_admin_membership", has_admin_membership
    )
    monkeypatch.setattr(auth_v2.mfa_service, "factors_for_user", factors_for_user)

    assert await auth_v2._mfa_login_state("user", "token", factors=None) == (
        False,
        True,
    )
    assert calls == ["has_admin_membership", "factors_for_user"]


@pytest.mark.asyncio
async def test_non_admin_never_reads_mfa_factors(monkeypatch):
    calls = []

    async def fake_run_db(fn, *args, **kwargs):
        calls.append(fn.__name__)
        return fn(*args, **kwargs)

    def has_admin_membership(_user_id):
        return False

    def factors_for_user(_token):
        raise AssertionError("non-admins have no MFA gate")

    monkeypatch.setattr(auth_v2, "run_db", fake_run_db)
    monkeypatch.setattr(
        auth_v2.mfa_service, "has_admin_membership", has_admin_membership
    )
    monkeypatch.setattr(auth_v2.mfa_service, "factors_for_user", factors_for_user)

    assert await auth_v2._mfa_login_state("user", "token", factors=None) == (
        False,
        False,
    )
    assert calls == ["has_admin_membership"]


def test_auth_repository_reuses_one_anon_client(monkeypatch):
    import app.repositories.auth.auth_repository as module

    created = []

    def fake_create_client(url, key):
        created.append((url, key))
        return object()

    monkeypatch.setattr(module, "create_client", fake_create_client)
    monkeypatch.setattr(module, "_anon_client", None)

    repository = AuthRepository()

    first = repository._client()
    second = repository._client()

    assert first is second
    assert len(created) == 1
