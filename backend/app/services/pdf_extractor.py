import pdfplumber
import io
import logging

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH = 50


def extract_text_from_pdf(file_bytes: bytes) -> tuple[str, bool]:
    """
    Extracts text from a digital PDF using pdfplumber.
    Returns (text, is_digital).
    If text is too short the PDF is scanned — caller uses Vision instead.
    """
    try:
        text_pages = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text.strip())

        full_text = "\n\n".join(text_pages).strip()

        if len(full_text) < MIN_TEXT_LENGTH:
            logger.info("PDF appears scanned — flagging for Vision fallback")
            return "", False

        logger.info(f"pdfplumber extracted {len(full_text)} characters")
        return full_text, True

    except Exception as e:
        logger.error(f"pdfplumber failed: {e}")
        return "", False