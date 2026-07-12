from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import usage


# -------------------------------------------------
# get_current_month
# -------------------------------------------------

def test_get_current_month():
    month = usage.get_current_month()

    assert isinstance(month, str)
    assert len(month) == 7
    assert "-" in month


# -------------------------------------------------
# check_usage_limit
# -------------------------------------------------

@pytest.mark.asyncio
async def test_check_usage_limit_under_limit(mocker):
    fake_result = SimpleNamespace(
        data={"invoice_count": 2}
    )

    execute = mocker.Mock(return_value=fake_result)

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.maybe_single.return_value = table
    table.execute = execute

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.services.usage.get_supabase",
        return_value=supabase,
    )

    await usage.check_usage_limit("user1", "starter")


@pytest.mark.asyncio
async def test_check_usage_limit_reached(mocker):
    fake_result = SimpleNamespace(
        data={"invoice_count": 999}
    )

    execute = mocker.Mock(return_value=fake_result)

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.maybe_single.return_value = table
    table.execute = execute

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.services.usage.get_supabase",
        return_value=supabase,
    )

    with pytest.raises(HTTPException) as exc:
        await usage.check_usage_limit("user1", "starter")

    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_check_usage_limit_database_error(mocker):
    execute = mocker.Mock(side_effect=Exception("db"))

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.maybe_single.return_value = table
    table.execute = execute

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.services.usage.get_supabase",
        return_value=supabase,
    )

    await usage.check_usage_limit("user1", "starter")


# -------------------------------------------------
# increment_usage
# -------------------------------------------------

@pytest.mark.asyncio
async def test_increment_usage_updates_existing_row(mocker):
    fake_result = SimpleNamespace(
        data=[{"invoice_count": 4}]
    )

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table

    table.execute = mocker.Mock(
        side_effect=[
            fake_result,
            SimpleNamespace(data={})
        ]
    )

    table.update.return_value = table

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.services.usage.get_supabase",
        return_value=supabase,
    )

    await usage.increment_usage("user1")

    table.update.assert_called_once_with(
        {"invoice_count": 5}
    )


@pytest.mark.asyncio
async def test_increment_usage_creates_first_row(mocker):
    fake_result = SimpleNamespace(data=[])

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table

    table.execute = mocker.Mock(
        side_effect=[
            fake_result,
            SimpleNamespace(data={})
        ]
    )

    table.insert.return_value = table

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.services.usage.get_supabase",
        return_value=supabase,
    )

    await usage.increment_usage("user1")

    table.insert.assert_called_once()


@pytest.mark.asyncio
async def test_increment_usage_database_error(mocker):
    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.execute.side_effect = Exception("db")

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.services.usage.get_supabase",
        return_value=supabase,
    )

    await usage.increment_usage("user1")


# -------------------------------------------------
# get_usage_summary
# -------------------------------------------------

@pytest.mark.asyncio
async def test_get_usage_summary_with_usage(mocker):
    fake_result = SimpleNamespace(
        data=[{"invoice_count": 3}]
    )

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.execute.return_value = fake_result

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.services.usage.get_supabase",
        return_value=supabase,
    )

    summary = await usage.get_usage_summary(
        "user1",
        "starter",
    )

    assert summary["used"] == 3
    assert summary["remaining"] == summary["limit"] - 3


@pytest.mark.asyncio
async def test_get_usage_summary_no_usage(mocker):
    fake_result = SimpleNamespace(data=[])

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.execute.return_value = fake_result

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.services.usage.get_supabase",
        return_value=supabase,
    )

    summary = await usage.get_usage_summary(
        "user1",
        "starter",
    )

    assert summary["used"] == 0
    assert summary["limit_reached"] is False


@pytest.mark.asyncio
async def test_get_usage_summary_database_error(mocker):
    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.execute.side_effect = Exception("db")

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.services.usage.get_supabase",
        return_value=supabase,
    )

    summary = await usage.get_usage_summary(
        "user1",
        "starter",
    )

    assert summary["used"] == 0