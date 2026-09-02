"""
============================================================
OCR Validation Module

Verification Module 1

Responsibilities
----------------
- Validate OCR quality
- Validate OCR confidence
- Detect scan issues
- Produce a VerificationResult

No database.

Consumes OCRResult produced by OCRService.
============================================================
"""

from __future__ import annotations

from decimal import Decimal

from app.models.domain.document import OCRResult
from app.services.verification.result import (
    VerificationResult,
)


class OCRValidation:
    """
    OCR verification module.
    """

    MIN_CONFIDENCE = Decimal("0.85")

    MIN_IMAGE_QUALITY = 70

    async def run(
        self,
        result: OCRResult,
    ) -> VerificationResult:
        """
        Validate OCR output.
        """

        passed = True

        score = 100

        reasons: list[str] = []

        positives: list[str] = []

        warnings: list[str] = []

        # -----------------------------------------
        # Confidence
        # -----------------------------------------

        if result.confidence_score < self.MIN_CONFIDENCE:
            passed = False

            score -= 30

            reasons.append(
                "Low OCR confidence."
            )

        else:
            positives.append(
                "OCR confidence acceptable."
            )

        # -----------------------------------------
        # Image quality
        # -----------------------------------------

        if result.image_quality < self.MIN_IMAGE_QUALITY:
            score -= 20

            warnings.append(
                "Poor image quality."
            )

        else:
            positives.append(
                "Image quality acceptable."
            )

        # -----------------------------------------
        # Scan
        # -----------------------------------------

        if result.is_scanned:
            warnings.append(
                "Document is scanned."
            )

        # -----------------------------------------
        # Handwriting
        # -----------------------------------------

        if result.is_handwritten:
            warnings.append(
                "Handwritten content detected."
            )

            score -= 10

        # -----------------------------------------
        # Raw text
        # -----------------------------------------

        if not result.raw_text.strip():
            passed = False

            score = 0

            reasons.append(
                "No OCR text extracted."
            )

        return VerificationResult(
            passed=passed,
            score=max(score, 0),
            confidence=int(
                result.confidence_score * 100
            ),
            summary="OCR validation completed.",
            reasons=reasons,
            positives=positives,
            warnings=warnings,
            metadata={
                "page_count": result.page_count,
                "engine": result.engine.value,
                "engine_version": result.engine_version,
                "processing_ms": result.processing_ms,
                "tokens_used": result.tokens_used,
            },
        )