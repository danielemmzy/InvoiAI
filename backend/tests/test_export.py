from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.invoice import StructuredDocument
from app.routers.export import (
    _fetch_structured,
    download_excel,
    download_csv,
    export_to_google_sheets,
)


def current_user():
    return AuthUser(
        id="user123",
        email="user@test.com",
        plan="starter",
    )


def sample_document():
    return StructuredDocument(
        industry="general",
        document_type="Invoice",
        sections={
            "header": {
                "vendor": "ACME",
            }
        },
        raw_totals={
            "total": 100,
        },
        extraction_confidence="high",
    )


#
# _fetch_structured()
#

@pytest.mark.asyncio
async def test_fetch_structured_success(mocker):

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = SimpleNamespace(
        data={
            "structured_data": sample_document().model_dump(),
            "status": "done",
            "file_name": "invoice.pdf",
        }
    )

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.export.get_supabase",
        return_value=supabase,
    )

    document, filename = await _fetch_structured(
        "invoice123",
        "user123",
    )

    assert isinstance(document, StructuredDocument)
    assert filename == "invoice.pdf"


@pytest.mark.asyncio
async def test_fetch_structured_not_found(mocker):

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = SimpleNamespace(
        data=None,
    )

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.export.get_supabase",
        return_value=supabase,
    )

    with pytest.raises(HTTPException) as exc:

        await _fetch_structured(
            "invoice123",
            "user123",
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_fetch_structured_processing(mocker):

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = SimpleNamespace(
        data={
            "structured_data": sample_document().model_dump(),
            "status": "processing",
            "file_name": "invoice.pdf",
        }
    )

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.export.get_supabase",
        return_value=supabase,
    )

    with pytest.raises(HTTPException) as exc:

        await _fetch_structured(
            "invoice123",
            "user123",
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_fetch_structured_database_failure(mocker):

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.side_effect = Exception(
        "database",
    )

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.export.get_supabase",
        return_value=supabase,
    )

    with pytest.raises(HTTPException) as exc:

        await _fetch_structured(
            "invoice123",
            "user123",
        )

    assert exc.value.status_code == 404


#
# download_excel()
#

@pytest.mark.asyncio
async def test_download_excel(mocker):

    document = sample_document()

    mocker.patch(
        "app.routers.export._fetch_structured",
        return_value=(document, "invoice.pdf"),
    )

    mocker.patch(
        "app.routers.export.export_to_excel",
        return_value=b"excel-data",
    )

    response = await download_excel.__wrapped__(
        request=None,
        invoice_id="invoice123",
        current_user=current_user(),
    )

    assert response.status_code == 200
    assert response.media_type.startswith(
        "application/vnd.openxmlformats"
    )

    assert "attachment" in response.headers["content-disposition"]


#
# download_csv()
#

@pytest.mark.asyncio
async def test_download_csv(mocker):

    document = sample_document()

    mocker.patch(
        "app.routers.export._fetch_structured",
        return_value=(document, "invoice.pdf"),
    )

    mocker.patch(
        "app.routers.export.export_to_csv",
        return_value=b"csv-data",
    )

    response = await download_csv.__wrapped__(
        request=None,
        invoice_id="invoice123",
        current_user=current_user(),
    )

    assert response.status_code == 200
    assert response.media_type == "text/csv"

    assert "attachment" in response.headers["content-disposition"]


#
# Google Sheets
#

@pytest.mark.asyncio
async def test_export_to_google_sheets_existing_url(mocker):

    document = sample_document()

    mocker.patch(
        "app.routers.export._fetch_structured",
        return_value=(document, "invoice.pdf"),
    )

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = SimpleNamespace(
        data={
            "sheets_url": "https://docs.google.com/test",
        }
    )

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.export.get_supabase",
        return_value=supabase,
    )

    export = mocker.patch(
        "app.routers.export.export_to_sheets",
    )

    response = await export_to_google_sheets.__wrapped__(
        request=None,
        invoice_id="invoice123",
        current_user=current_user(),
    )

    export.assert_not_called()

    assert response["message"] == "Existing spreadsheet returned"


@pytest.mark.asyncio
async def test_export_to_google_sheets_new_sheet(mocker):

    document = sample_document()

    mocker.patch(
        "app.routers.export._fetch_structured",
        return_value=(document, "invoice.pdf"),
    )

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table

    table.execute.side_effect = [
        SimpleNamespace(data={}),
        SimpleNamespace(data={}),
    ]

    table.update.return_value = table

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.export.get_supabase",
        return_value=supabase,
    )

    mocker.patch(
        "app.routers.export.export_to_sheets",
        return_value="https://docs.google.com/new-sheet",
    )

    response = await export_to_google_sheets.__wrapped__(
        request=None,
        invoice_id="invoice123",
        current_user=current_user(),
    )

    assert response["sheets_url"] == "https://docs.google.com/new-sheet"


@pytest.mark.asyncio
async def test_export_to_google_sheets_failure(mocker):

    document = sample_document()

    mocker.patch(
        "app.routers.export._fetch_structured",
        return_value=(document, "invoice.pdf"),
    )

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = SimpleNamespace(
        data={}
    )

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.export.get_supabase",
        return_value=supabase,
    )

    mocker.patch(
        "app.routers.export.export_to_sheets",
        side_effect=Exception("google"),
    )

    with pytest.raises(HTTPException) as exc:

        await export_to_google_sheets.__wrapped__(
            request=None,
            invoice_id="invoice123",
            current_user=current_user(),
        )

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_export_to_google_sheets_save_failure_is_non_fatal(mocker):

    document = sample_document()

    mocker.patch(
        "app.routers.export._fetch_structured",
        return_value=(document, "invoice.pdf"),
    )

    table = mocker.Mock()

    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table

    table.execute.side_effect = [
        SimpleNamespace(data={}),
        Exception("save failed"),
    ]

    table.update.return_value = table

    supabase = mocker.Mock()
    supabase.table.return_value = table

    mocker.patch(
        "app.routers.export.get_supabase",
        return_value=supabase,
    )

    mocker.patch(
        "app.routers.export.export_to_sheets",
        return_value="https://docs.google.com/test",
    )

    response = await export_to_google_sheets.__wrapped__(
        request=None,
        invoice_id="invoice123",
        current_user=current_user(),
    )

    assert response["sheets_url"] == "https://docs.google.com/test"