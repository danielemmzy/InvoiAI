from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.routers.invoice import (
    get_invoice,
    delete_invoice,
)


@pytest.mark.asyncio
async def test_get_invoice_success(mocker):

    current_user = AuthUser(
        id="123",
        email="user@test.com",
    )

    result = SimpleNamespace(
        data={
            "id": "abc",
            "status": "completed",
            "document_type": "Invoice",
            "structured_data": {
                "industry": "general",
                "document_type": "Invoice",
                "sections": {},
                "raw_totals": {},
                "extraction_confidence": "high",
            },
            "validation_warnings": [],
        }
    )

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = result

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.invoice.get_supabase",
        return_value=supabase,
    )

    response = await get_invoice.__wrapped__(
        request=None,
        invoice_id="abc",
        current_user=current_user,
    )

    assert response.invoice_id == "abc"
    assert response.status == "completed"
    assert response.document_type == "Invoice"


@pytest.mark.asyncio
async def test_get_invoice_not_found(mocker):

    current_user = AuthUser(
        id="123",
        email="user@test.com",
    )

    result = SimpleNamespace(data=None)

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = result

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.invoice.get_supabase",
        return_value=supabase,
    )

    with pytest.raises(HTTPException) as exc:
        await get_invoice.__wrapped__(
            request=None,
            invoice_id="abc",
            current_user=current_user,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_invoice_db_failure(mocker):

    current_user = AuthUser(
        id="123",
        email="user@test.com",
    )

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.side_effect = Exception("db")

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.invoice.get_supabase",
        return_value=supabase,
    )

    with pytest.raises(HTTPException) as exc:
        await get_invoice.__wrapped__(
            request=None,
            invoice_id="abc",
            current_user=current_user,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_invoice_success(mocker):

    current_user = AuthUser(
        id="123",
        email="user@test.com",
    )

    result = SimpleNamespace(
        data={
            "user_id": "123",
            "file_url": "invoice.pdf",
        }
    )

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = result
    table.delete.return_value = table

    storage = mocker.Mock()

    supabase = mocker.Mock()
    supabase.table.return_value = table
    supabase.storage.from_.return_value = storage

    mocker.patch(
        "app.routers.invoice.get_supabase",
        return_value=supabase,
    )

    response = await delete_invoice.__wrapped__(
        request=None,
        invoice_id="abc",
        current_user=current_user,
    )

    assert response["message"] == "Deleted successfully"

    supabase.storage.from_.assert_called_once_with("invoices")
    storage.remove.assert_called_once_with(["invoice.pdf"])
    table.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_invoice_not_found(mocker):

    current_user = AuthUser(
        id="123",
        email="user@test.com",
    )

    result = SimpleNamespace(data=None)

    table = mocker.Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = result

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.invoice.get_supabase",
        return_value=supabase,
    )

    with pytest.raises(HTTPException) as exc:
        await delete_invoice.__wrapped__(
            request=None,
            invoice_id="abc",
            current_user=current_user,
        )

    assert exc.value.status_code == 404