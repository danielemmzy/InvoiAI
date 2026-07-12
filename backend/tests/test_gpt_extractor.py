import json
from types import SimpleNamespace

import pytest

from app.services.gpt_extractor import (
    build_prompt,
    extract_from_text,
    extract_from_image,
    _empty_document,
    _build_raw_text_summary,
)


def fake_response(data):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(data)
                )
            )
        ]
    )


def test_build_prompt():
    prompt = build_prompt("general")

    assert "General" in prompt
    assert "document extraction engine" in prompt


def test_empty_document():
    doc = _empty_document("general")

    assert doc.industry == "general"
    assert doc.document_type == "Unknown"
    assert doc.sections == {}
    assert doc.raw_totals == {}
    assert doc.extraction_confidence == "low"


def test_build_raw_text_summary():
    doc = _empty_document("general")

    doc.document_type = "Invoice"
    doc.sections = {
        "header": {
            "invoice": "INV001"
        },
        "line_items": [
            {
                "description": "Laptop",
                "amount": 500,
            }
        ]
    }
    doc.raw_totals = {
        "total": 500
    }

    text = _build_raw_text_summary(doc)

    assert "Invoice" in text
    assert "Laptop" in text
    assert "total: 500" in text


@pytest.mark.asyncio
async def test_extract_from_text_success(mocker):

    response = fake_response(
        {
            "document_type": "Invoice",
            "sections": {
                "header": {
                    "invoice": "INV001"
                }
            },
            "raw_totals": {
                "total": 100
            },
            "extraction_confidence": "high",
        }
    )

    create = mocker.AsyncMock(
        return_value=response
    )

    mocker.patch(
        "app.services.gpt_extractor.client.chat.completions.create",
        create,
    )

    doc = await extract_from_text(
        "invoice text",
        "general",
    )

    assert doc.document_type == "Invoice"
    assert doc.raw_totals["total"] == 100
    assert doc.extraction_confidence == "high"


@pytest.mark.asyncio
async def test_extract_from_text_bad_json(mocker):

    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="not json"
                )
            )
        ]
    )

    create = mocker.AsyncMock(
        return_value=response
    )

    mocker.patch(
        "app.services.gpt_extractor.client.chat.completions.create",
        create,
    )

    doc = await extract_from_text(
        "invoice",
        "general",
    )

    assert doc.document_type == "Unknown"


@pytest.mark.asyncio
async def test_extract_from_text_exception(mocker):

    create = mocker.AsyncMock(
        side_effect=Exception("boom")
    )

    mocker.patch(
        "app.services.gpt_extractor.client.chat.completions.create",
        create,
    )

    doc = await extract_from_text(
        "invoice",
        "general",
    )

    assert doc.document_type == "Unknown"


@pytest.mark.asyncio
async def test_extract_from_image_success(mocker):

    response = fake_response(
        {
            "document_type": "Receipt",
            "sections": {},
            "raw_totals": {
                "total": 25
            },
            "extraction_confidence": "medium",
        }
    )

    create = mocker.AsyncMock(
        return_value=response
    )

    mocker.patch(
        "app.services.gpt_extractor.client.chat.completions.create",
        create,
    )

    raw_text, doc = await extract_from_image(
        b"image",
        "image/png",
        "general",
    )

    assert doc.document_type == "Receipt"
    assert "Document Type" in raw_text


@pytest.mark.asyncio
async def test_extract_from_image_bad_json(mocker):

    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="bad json"
                )
            )
        ]
    )

    create = mocker.AsyncMock(
        return_value=response
    )

    mocker.patch(
        "app.services.gpt_extractor.client.chat.completions.create",
        create,
    )

    raw_text, doc = await extract_from_image(
        b"image",
        "image/png",
        "general",
    )

    assert raw_text == ""
    assert doc.document_type == "Unknown"


@pytest.mark.asyncio
async def test_extract_from_image_exception(mocker):

    create = mocker.AsyncMock(
        side_effect=Exception("boom")
    )

    mocker.patch(
        "app.services.gpt_extractor.client.chat.completions.create",
        create,
    )

    raw_text, doc = await extract_from_image(
        b"image",
        "image/png",
        "general",
    )

    assert raw_text == ""
    assert doc.document_type == "Unknown"