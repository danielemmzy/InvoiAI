from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth import AuthUser, get_current_user


def credentials():
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="fake-token",
    )

@pytest.mark.asyncio
async def test_get_current_user_success(mocker):

    user = SimpleNamespace(
        id="123",
        email="user@example.com"
    )

    auth_response = SimpleNamespace(user=user)
    profile_response = SimpleNamespace(
        data={"plan": "starter"}
    )

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = profile_response

    supabase = mocker.Mock()
    supabase.auth.get_user.return_value = auth_response
    supabase.table.return_value = table

    mocker.patch(
        "app.core.auth.get_supabase",
        return_value=supabase,
    )

    current_user = await get_current_user(credentials())

    assert current_user.id == "123"
    assert current_user.email == "user@example.com"
    assert current_user.plan == "starter"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mocker):

    response = SimpleNamespace(user=None)

    supabase = mocker.Mock()
    supabase.auth.get_user.return_value = response

    mocker.patch(
        "app.core.auth.get_supabase",
        return_value=supabase,
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials())

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_supabase_failure(mocker):

    supabase = mocker.Mock()
    supabase.auth.get_user.side_effect = Exception(
        "network"
    )

    mocker.patch(
        "app.core.auth.get_supabase",
        return_value=supabase,
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials())

    assert exc.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user_default_plan(mocker):

    user = SimpleNamespace(
        id="123",
        email="test@example.com",
    )

    auth_response = SimpleNamespace(user=user)

    profile = SimpleNamespace(data=None)

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = profile

    supabase = mocker.Mock()
    supabase.auth.get_user.return_value = auth_response
    supabase.table.return_value = table

    mocker.patch(
        "app.core.auth.get_supabase",
        return_value=supabase,
    )

    current_user = await get_current_user(credentials())

    assert current_user.plan == "free"

@pytest.mark.asyncio
async def test_get_current_user_profile_lookup_failure(mocker):

    user = SimpleNamespace(
        id="123",
        email="test@example.com",
    )

    auth_response = SimpleNamespace(user=user)

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.side_effect = Exception(
        "database"
    )

    supabase = mocker.Mock()
    supabase.auth.get_user.return_value = auth_response
    supabase.table.return_value = table

    mocker.patch(
        "app.core.auth.get_supabase",
        return_value=supabase,
    )

    current_user = await get_current_user(credentials())

    assert current_user.plan == "free"

def test_auth_user_defaults():
    user = AuthUser(
        id="1",
        email="user@test.com",
    )

    assert user.id == "1"
    assert user.email == "user@test.com"
    assert user.plan == "free"