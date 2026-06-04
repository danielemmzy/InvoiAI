import pdfplumber
import io
import logging

logger = logging.getLogger(__name__)

# If extracted text is shorter than this we treat the PDF
# as scanned/image-based and fall back to GPT-4o Vision.
MIN_TEXT_LENGTH = 50


def extract_text_from_pdf(file_bytes: bytes) -> tuple[str, bool]:
    """
    Attempts to extract text from a PDF using pdfplumber.

    Returns:
        tuple:
            - text (str): extracted text, empty string if failed
            - is_digital (bool): True if real text found, False if scanned

    Why check MIN_TEXT_LENGTH?
        - Scanned PDFs technically open with pdfplumber but return empty/near-empty text
        - We detect this and flag for GPT-4o Vision fallback
    """
    try:
        text_pages = []

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                # extract_text() returns None if page has no text layer
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text.strip())

        full_text = "\n\n".join(text_pages).strip()

        if len(full_text) < MIN_TEXT_LENGTH:
            logger.info("PDF appears scanned or image-based, flagging for Vision fallback")
            return "", False

        logger.info(f"pdfplumber extracted {len(full_text)} characters successfully")
        return full_text, True

    except Exception as e:
        logger.error(f"pdfplumber extraction failed: {e}")
        return "", False