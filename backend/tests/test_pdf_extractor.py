from types import SimpleNamespace

from app.services.pdf_extractor import extract_text_from_pdf


def test_extract_text_success(mocker):
    page = mocker.Mock()
    page.extract_text.return_value = (
        "This is a PDF with enough text to exceed the minimum "
        "length required for extraction."
    )

    pdf = SimpleNamespace(pages=[page])

    open_mock = mocker.patch(
        "app.services.pdf_extractor.pdfplumber.open"
    )
    open_mock.return_value.__enter__.return_value = pdf

    text, digital = extract_text_from_pdf(b"fake")

    assert digital is True
    assert "This is a PDF" in text


def test_extract_text_scanned_pdf(mocker):
    page = mocker.Mock()
    page.extract_text.return_value = "Too short"

    pdf = SimpleNamespace(pages=[page])

    open_mock = mocker.patch(
        "app.services.pdf_extractor.pdfplumber.open"
    )
    open_mock.return_value.__enter__.return_value = pdf

    text, digital = extract_text_from_pdf(b"fake")

    assert text == ""
    assert digital is False


def test_extract_text_none_pages(mocker):
    page = mocker.Mock()
    page.extract_text.return_value = None

    pdf = SimpleNamespace(pages=[page])

    open_mock = mocker.patch(
        "app.services.pdf_extractor.pdfplumber.open"
    )
    open_mock.return_value.__enter__.return_value = pdf

    text, digital = extract_text_from_pdf(b"fake")

    assert text == ""
    assert digital is False


def test_extract_text_exception(mocker):
    mocker.patch(
        "app.services.pdf_extractor.pdfplumber.open",
        side_effect=Exception("boom"),
    )

    text, digital = extract_text_from_pdf(b"fake")

    assert text == ""
    assert digital is False