"""Supabase Auth SDK calls are synchronous; async endpoints must not call them inline."""

import threading

import pytest

from app.repositories.auth.auth_repository import AuthRepository


@pytest.mark.asyncio
async def test_signup_runs_off_the_event_loop(monkeypatch):
    repo = AuthRepository()
    seen = {}

    class FakeAuth:
        def sign_up(self, payload):
            seen["thread"] = threading.get_ident()
            seen["payload"] = payload
            return {"user": "created"}

    monkeypatch.setattr(
        repo, "_client", lambda: type("C", (), {"auth": FakeAuth()})()
    )

    result = await repo.signup("person@example.com", "secret")

    assert result == {"user": "created"}
    assert seen["payload"]["email"] == "person@example.com"
    assert seen["thread"] != threading.get_ident()


@pytest.mark.asyncio
async def test_admin_confirm_email_runs_off_the_event_loop(monkeypatch):
    repo = AuthRepository()
    seen = {}

    class FakeAdmin:
        def update_user_by_id(self, user_id, values):
            seen["thread"] = threading.get_ident()
            seen["values"] = values
            return {"id": user_id, **values}

    class FakeClient:
        auth = type("A", (), {"admin": FakeAdmin()})()

    import app.core.supabase as supabase_module

    monkeypatch.setattr(supabase_module, "get_supabase", lambda: FakeClient())

    result = await repo.admin_confirm_email("user-1")

    assert result["email_confirm"] is True
    assert seen["thread"] != threading.get_ident()
