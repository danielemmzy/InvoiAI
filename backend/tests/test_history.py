from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.routers.history import get_history


@pytest.mark.asyncio
async def test_get_history_success(mocker):

    current_user = AuthUser(
        id="123",
        email="user@test.com",
    )

    result = SimpleNamespace(
        data=[
            {
                "id": "1",
                "file_name": "invoice.pdf",
                "status": "completed",
            }
        ]
    )

    query = mocker.Mock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = result

    supabase = mocker.Mock()
    supabase.table.return_value = query

    mocker.patch(
        "app.routers.history.get_supabase",
        return_value=supabase,
    )

    response = await get_history.__wrapped__(
    request=None,
    current_user=current_user,
    industry=None,
    limit=20,
    offset=0,)

    assert response["count"] == 1
    assert response["documents"][0]["id"] == "1"


@pytest.mark.asyncio
async def test_get_history_with_industry_filter(mocker):

    current_user = AuthUser(
        id="123",
        email="user@test.com",
    )

    result = SimpleNamespace(data=[])

    query = mocker.Mock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = result

    supabase = mocker.Mock()
    supabase.table.return_value = query

    mocker.patch(
        "app.routers.history.get_supabase",
        return_value=supabase,
    )

    await get_history.__wrapped__(
    request=None,
    current_user=current_user,
    industry="healthcare",
    limit=20,
    offset=0,)

    query.eq.assert_any_call(
        "industry",
        "healthcare",
    )


@pytest.mark.asyncio
async def test_get_history_db_failure(mocker):

    current_user = AuthUser(
        id="123",
        email="user@test.com",
    )

    query = mocker.Mock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.side_effect = Exception("db")

    supabase = mocker.Mock()
    supabase.table.return_value = query

    mocker.patch(
        "app.routers.history.get_supabase",
        return_value=supabase,
    )

    with pytest.raises(HTTPException) as exc:
        await get_history.__wrapped__(
    request=None,
    current_user=current_user,
)

    assert exc.value.status_code == 500