import base64
import json
import asyncio
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core import auth
from app.core import supabase as supabase_core
from app.core import mfa as mfa_guards
from app.services.auth.mfa_security import (
    generate_recovery_codes,
    hash_recovery_code,
    is_recent_aal2,
)
from app.services.auth import mfa_service


def test_recovery_codes_are_ten_unique_one_time_values_with_only_hashes_persisted():
    codes, hashes = generate_recovery_codes()

    assert len(codes) == len(hashes) == 10
    assert len(set(codes)) == len(set(hashes)) == 10
    assert hashes == [hash_recovery_code(code) for code in codes]
    assert not set(codes).intersection(hashes)


def test_only_a_recent_aal2_token_counts_as_step_up():
    now = 1_800_000_000

    assert is_recent_aal2("aal2", now - 299, now=now)
    assert not is_recent_aal2("aal1", now - 1, now=now)
    assert not is_recent_aal2("aal2", now - 600, now=now)
    assert not is_recent_aal2("aal2", None, now=now)


def test_recent_step_up_uses_totp_authentication_time_not_refreshed_token_time():
    now = 1_800_000_000

    assert is_recent_aal2("aal2", now - 299, now=now)
    assert not is_recent_aal2("aal2", now - 600, now=now)


def test_access_token_validation_preserves_verified_supabase_assurance_claims(monkeypatch):
    from app.services.auth import verification_service

    claims = {
        "aal": "aal2",
        "iat": 1_800_000_299,
        "amr": [{"method": "totp", "timestamp": 1_800_000_000}],
        "session_id": "0dd4f4c1-3231-4ca2-8bc7-674f234b3aa0",
    }
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(b"sig").decode().rstrip("=")
    token = f"{header}.{payload}.{signature}"
    user = SimpleNamespace(
        id="0dd4f4c1-3231-4ca2-8bc7-674f234b3aa0",
        email="admin@example.com",
        app_metadata={},
        user_metadata={},
        email_confirmed_at="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr(auth, "get_supabase", lambda: SimpleNamespace(auth=SimpleNamespace(
        get_user=lambda _token: SimpleNamespace(user=user)
    )))
    monkeypatch.setattr(verification_service, "resolve_email_verified", lambda *_args, **_kwargs: True)

    validated = auth.validate_access_token(token)

    assert validated.aal == "aal2"
    assert validated.token_issued_at == claims["iat"]
    assert validated.session_id == claims["session_id"]
    assert validated.mfa_verified_at == claims["amr"][0]["timestamp"]


def test_user_auth_client_is_request_scoped_and_uses_only_the_verified_access_token(monkeypatch):
    clients = []

    def create_client(_url, _key):
        client = SimpleNamespace(auth=SimpleNamespace(set_session=lambda access, refresh: (access, refresh)))
        clients.append(client)
        return client

    monkeypatch.setattr(supabase_core, "create_client", create_client)
    monkeypatch.setattr(supabase_core.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(supabase_core.settings, "supabase_anon_key", "anon")

    first = supabase_core.get_user_supabase("first-access")
    second = supabase_core.get_user_supabase("second-access")

    assert first is clients[0] and second is clients[1] and first is not second
    assert first.auth.set_session("first-access", "") == ("first-access", "")
    assert second.auth.set_session("second-access", "") == ("second-access", "")


def test_recovery_consumption_is_bound_to_user_session_and_hashed_code(monkeypatch):
    calls = []

    class Rpc:
        def execute(self):
            return SimpleNamespace(data=True)

    class Database:
        def rpc(self, name, params):
            calls.append((name, params))
            return Rpc()

    monkeypatch.setattr(mfa_service, "get_supabase", lambda: Database())

    assert mfa_service.consume_recovery_code("user-1", "session-1", "ABCD-EF01")
    assert calls == [(
        "consume_auth_mfa_recovery_code",
        {
            "p_user_id": "user-1",
            "p_session_id": "session-1",
            "p_code_hash": hash_recovery_code("ABCD-EF01"),
        },
    )]


def test_admin_without_verified_totp_is_blocked_from_business_routes(monkeypatch):
    user = SimpleNamespace(id="user-1", aal="aal1")
    monkeypatch.setattr(auth, "validate_access_token", lambda _token: user)
    monkeypatch.setattr(mfa_service, "has_admin_membership", lambda _user_id: True)
    monkeypatch.setattr(mfa_service, "factors_for_user", lambda _token: SimpleNamespace(totp=[]))
    request = Request({"type": "http", "method": "GET", "path": "/api/v2/documents", "headers": []})

    with pytest.raises(HTTPException) as raised:
        asyncio.run(auth.get_current_user(request, SimpleNamespace(credentials="access-token")))

    assert raised.value.status_code == 403
    assert raised.value.detail["code"] == "MFA_ENROLLMENT_REQUIRED"


def test_admin_without_verified_totp_can_reach_mfa_setup(monkeypatch):
    user = SimpleNamespace(id="user-1", aal="aal1")
    monkeypatch.setattr(auth, "validate_access_token", lambda _token: user)
    monkeypatch.setattr(mfa_service, "has_admin_membership", lambda _user_id: True)
    monkeypatch.setattr(mfa_service, "factors_for_user", lambda _token: SimpleNamespace(totp=[]))
    request = Request({"type": "http", "method": "POST", "path": "/api/v2/auth/mfa/enroll", "headers": []})

    assert asyncio.run(auth.get_current_user(request, SimpleNamespace(credentials="access-token"))) is user


def test_admin_step_up_requires_recent_totp_amr_or_session_recovery_grant(monkeypatch):
    now = int(time.time())
    user = SimpleNamespace(
        id="user-1", aal="aal2", mfa_verified_at=now - 30, session_id="session-1"
    )
    context = SimpleNamespace(role="admin")
    request = Request({"type": "http", "method": "PATCH", "path": "/api/v2/organization-settings", "headers": []})
    monkeypatch.setattr(mfa_guards.mfa_service, "has_recovery_step_up", lambda *_args: False)

    assert asyncio.run(mfa_guards.require_fresh_mfa(request, user, context)) is None

    user.mfa_verified_at = now - 600
    with pytest.raises(HTTPException) as raised:
        asyncio.run(mfa_guards.require_fresh_mfa(request, user, context))
    assert raised.value.status_code == 403
    assert raised.value.detail["code"] == "MFA_STEP_UP_REQUIRED"
