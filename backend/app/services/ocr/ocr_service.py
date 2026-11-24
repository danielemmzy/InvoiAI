from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from uuid import UUID

from app.core.enum.database import (
    DocumentStatus,
    DocumentType,
    OCREngineType,
    PipelineStage,
)

from app.core.enum.finance import OwnerType

from app.core.supabase import get_supabase

from app.integrations.openai.openai_ocr_service import (
    OpenAIOCRService,
)

from app.models.domain.document import OCRResult

from app.repositories.document.document_repository import (
    DocumentRepository,
)

from app.repositories.document.ocr_repository import (
    OCRRepository,
)

from app.services.document.classifier_service import (
    DocumentClassifierService,
)

from app.services.document.workflow_router import (
    route_for,
)

from app.services.extraction.personal_extractor import (
    PersonalExtractor,
)

from app.services.extraction.extraction_service import (
    ExtractionService,
)

from app.services.extraction.extraction_engine import (
    ExtractionEngine,
)

from app.services.storage.storage import (
    StorageService,
)

from app.workers.analysis_worker import (
    AnalysisWorker,
)

from app.core.ai_config import EXTRACTION_MODEL


logger = logging.getLogger(__name__)


FILE_TYPE_MIME_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


from app.core.db import execute

class OCRService:
    """
    OCR orchestration service.

    Responsibilities
    ----------------
    - Load document
    - Download file
    - Execute OpenAI OCR
    - Persist OCR result
    - Update pipeline
    - Classify document
    - Route workflow
    - Trigger AI analysis

    No SQL business logic belongs here.
    """

    def __init__(
        self,
        *,
        document_repository: DocumentRepository,
        ocr_repository: OCRRepository,
        storage_service: StorageService,
        provider: OpenAIOCRService,
        analysis_worker: AnalysisWorker,
        classifier: DocumentClassifierService | None = None,
        extraction_service: ExtractionService | None = None,
    ) -> None:
        self.document_repository = document_repository
        self.ocr_repository = ocr_repository
        self.storage = storage_service
        self.provider = provider
        self.analysis_worker = analysis_worker

        self.classifier = (
            classifier
            or DocumentClassifierService()
        )

        self.extraction_service = (
            extraction_service
            or ExtractionService(
                ExtractionEngine()
            )
        )

    @staticmethod
    def _enum_value(
        value: object,
    ) -> str:
        """
        Return the underlying enum value whether the model
        contains an Enum instance or a plain string.
        """
        if isinstance(value, Enum):
            return str(value.value)

        return str(value)

    @classmethod
    def _mime_type_for_file_type(
        cls,
        file_type: object,
    ) -> str:
        file_type_value = (
            cls._enum_value(file_type)
            .lower()
            .strip()
        )

        mime_type = FILE_TYPE_MIME_TYPES.get(
            file_type_value
        )

        if mime_type is None:
            raise ValueError(
                "Unsupported OCR file type: "
                f"{file_type_value}"
            )

        return mime_type

    # =====================================================
    # OCR
    # =====================================================

    async def run_ocr(
        self,
        *,
        document_id: UUID,
        trigger_analysis: bool = True,
    ) -> OCRResult:
        """
        Execute the complete OCR pipeline for one document.
        """
        try:
            return await self._run_ocr(
                document_id=document_id,
                trigger_analysis=trigger_analysis,
            )
        except Exception as exc:
            error_message = (
                f"Document processing failed: {exc}"
            )[:2000]

            logger.exception(
                "Document processing failed: document_id=%s",
                document_id,
            )

            try:
                await self.document_repository.mark_failed(
                    document_id,
                    error_message,
                )
                await self.document_repository.update(
                    document_id,
                    {"capture_status": "failed", "capture_progress": 100, "capture_error": error_message},
                )
            except Exception:
                logger.exception(
                    "Unable to persist FAILED state: document_id=%s",
                    document_id,
                )

            raise

    async def _run_ocr(
        self,
        *,
        document_id: UUID,
        trigger_analysis: bool = True,
    ) -> OCRResult:
        document = await self.document_repository.get_document(
            document_id,
        )

        if document is None:
            raise ValueError(
                "Document not found."
            )

        if not trigger_analysis:
            await self.document_repository.update(
                document.id,
                {"capture_status": "processing", "capture_progress": 0, "capture_error": None},
            )

        await self.document_repository.update_document_status(
            document.id,
            DocumentStatus.OCR_RUNNING,
        )

        await self.document_repository.update_processing_state(
            document.id,
            step="reading",
            message="Reading your document and checking its structure",
            progress=8,
        )
        if not trigger_analysis:
            await self.document_repository.update(document.id, {"capture_progress": 8})

        await self.document_repository.update_pipeline_stage(
            document.id,
            PipelineStage.OCR,
        )

        await self.document_repository.update_processing_state(
            document.id,
            step="ocr",
            message="Extracting text, tables, and document details",
            progress=18,
        )

        file_bytes = await self.storage.download_document(
            document.file_url,
        )

        if not file_bytes:
            raise ValueError(
                "Document file is empty or could not be downloaded."
            )

        mime_type = self._mime_type_for_file_type(
            document.file_type,
        )

        await self.document_repository.update_processing_state(
            document.id,
            step="ocr",
            message="Reading the document with AI",
            progress=28,
        )
        if not trigger_analysis:
            await self.document_repository.update(document.id, {"capture_progress": 28})

        started = time.perf_counter()

        ocr_document = await self.provider.process_document(
            content=file_bytes,
            mime_type=mime_type,
        )

        processing_ms = int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

        raw_text = (
            ocr_document.raw_text
            or ""
        )

        pages: list[dict] = []

        for page in ocr_document.pages:
            pages.append(
                {
                    "page_number": page.page_number,
                    "text": page.text,
                }
            )

        tables = list(
            ocr_document.tables_detected
        )

        languages = list(
            ocr_document.languages
        )

        file_type_value = (
            self._enum_value(
                document.file_type
            )
            .lower()
        )

        confidence = float(
            ocr_document.confidence
        )

        result = OCRResult(
            document_id=document.id,
            org_id=document.org_id,
            raw_text=raw_text,
            page_count=len(
                ocr_document.pages
            ),
            pages=pages,
            tables_detected=tables,
            key_value_pairs={},
            language_detected=(
                ",".join(
                    sorted(languages)
                )
                if languages
                else None
            ),
            is_handwritten=False,
            is_scanned=(
                file_type_value == "pdf"
            ),
            has_tables=bool(tables),
            has_signatures=False,
            image_quality=100,
            engine=OCREngineType.GPT4O_VISION,
            engine_version=EXTRACTION_MODEL,
            confidence_score=Decimal(
                str(
                    round(
                        confidence,
                        4,
                    )
                )
            ),
            processing_ms=processing_ms,
            tokens_used=0,
        )

        # =================================================
        # Structured extraction
        # =================================================

        await self.document_repository.update_processing_state(
            document.id,
            step="extraction",
            message="Structuring document fields, totals, and line items",
            progress=32,
        )
        if not trigger_analysis:
            await self.document_repository.update(document.id, {"capture_progress": 32})

        _, structured = await self.extraction_service.extract(
            file_bytes=file_bytes,
            mime_type=mime_type,
            industry=document.industry or "general",
            raw_text=raw_text,
        )

        image_disagreement_warnings = (
            await self.extraction_service.compare_ocr_to_image(
                file_bytes=file_bytes,
                mime_type=mime_type,
                industry=document.industry or "general",
                structured_from_ocr=structured,
            )
        )

        extracted_document = (
            structured.sections.get("document")
            or {}
        )

        extracted_line_items = (
            structured.sections.get("line_items")
            or []
        )

        if not isinstance(
            extracted_document,
            dict,
        ):
            extracted_document = {}

        if not isinstance(
            extracted_line_items,
            list,
        ):
            extracted_line_items = []

        def _clean(value):
            if value is None:
                return None

            text = str(value).strip()

            return text or None

        def _number(value):
            if value is None or value == "":
                return None

            try:
                cleaned = (
                    str(value)
                    .strip()
                    .replace(",", "")
                )

                for symbol in (
                    "$",
                    "₦",
                    "€",
                    "£",
                ):
                    cleaned = cleaned.replace(
                        symbol,
                        "",
                    )

                return Decimal(cleaned)

            except (
                InvalidOperation,
                TypeError,
                ValueError,
            ):
                return None

        def _rate(value):
            number = _number(value)

            if number is None:
                return None

            if number > Decimal("1"):
                number /= Decimal("100")

            if (
                number < Decimal("0")
                or number > Decimal("1")
            ):
                return None

            return number

        def _date(value):
            if value is None:
                return None

            from datetime import date as date_type

            if isinstance(
                value,
                date_type,
            ):
                return value.isoformat()

            text = str(value).strip()

            if not text:
                return None

            for fmt in (
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%d %B %Y",
                "%d %b %Y",
                "%B %d, %Y",
                "%b %d, %Y",
            ):
                try:
                    return datetime.strptime(
                        text,
                        fmt,
                    ).date().isoformat()
                except ValueError:
                    continue

            # Never pass an unparsed OCR string to a PostgreSQL DATE column.
            # Unknown/ambiguous formats are treated as missing and can be
            # corrected by the user in the document capture editor.
            logger.warning("Ignoring unrecognized OCR date value: %r", text)
            return None

        totals = (
            structured.raw_totals
            if isinstance(
                structured.raw_totals,
                dict,
            )
            else {}
        )

        extracted_update = {
            "vendor_name": _clean(
                extracted_document.get(
                    "vendor_name"
                )
            ),
            "document_number": _clean(
                extracted_document.get(
                    "document_number"
                )
            ),
            "document_date": _date(
                extracted_document.get(
                    "document_date"
                )
            ),
            "due_date": _date(
                extracted_document.get(
                    "due_date"
                )
            ),
            "currency": _clean(
                extracted_document.get(
                    "currency"
                )
            ),
            "payment_terms": _clean(
                extracted_document.get(
                    "payment_terms"
                )
            ),
            "payment_method": _clean(
                extracted_document.get(
                    "payment_method"
                )
            ),
            "subtotal": _number(
                totals.get("subtotal")
            ),
            "tax_amount": _number(
                totals.get("tax_amount")
            ),
            "tax_rate": _rate(
                totals.get("tax_rate")
            ),
            "discount_amount": _number(
                totals.get("discount_amount")
            ),
            "total_amount": _number(
                totals.get("total_amount")
            ),
            "amount_paid": _number(
                totals.get("amount_paid")
            ),
            "amount_due": _number(
                totals.get("amount_due")
            ),
        }

        # =================================================
        # Normalize line items
        # =================================================

        normalized_items = []
        line_amounts: list[Decimal] = []
        incomplete_line_items = False

        for index, item in enumerate(
            extracted_line_items,
            start=1,
        ):
            if not isinstance(
                item,
                dict,
            ):
                continue

            description = _clean(
                item.get("description")
            )

            if not description:
                incomplete_line_items = True
                continue

            quantity = _number(
                item.get("quantity")
            )

            unit_price = _number(
                item.get("unit_price")
            )

            amount = _number(
                item.get("amount")
            )

            if quantity is None:
                quantity = Decimal("1")

            if (
                amount is None
                and unit_price is not None
            ):
                amount = (
                    quantity
                    * unit_price
                )

            if (
                unit_price is None
                and amount is not None
                and quantity != 0
            ):
                unit_price = (
                    amount
                    / quantity
                )

            if (
                unit_price is None
                or amount is None
            ):
                incomplete_line_items = True
                continue

            row = {
                "description": description,
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": amount,
                "position": index,
                "metadata": item,
            }

            for key in (
                "tax_rate",
                "tax_amount",
                "discount",
            ):
                value = item.get(key)

                numeric = (
                    _rate(value)
                    if key == "tax_rate"
                    else _number(value)
                )

                if numeric is not None:
                    row[key] = numeric

            normalized_items.append(row)
            line_amounts.append(amount)

        # =================================================
        # Financial reconciliation
        # =================================================

        reconciliation_warnings: list[str] = list(
            image_disagreement_warnings
        )

        # Repeated identical rows are a common vision extraction failure.
        # Do not silently delete them because identical products can be real;
        # instead flag the document for human verification.
        if len(normalized_items) >= 3:
            signatures = [
                (str(item.get("description") or "").strip().casefold(), str(item.get("quantity")), str(item.get("unit_price")), str(item.get("amount")))
                for item in normalized_items
            ]
            if len(set(signatures)) == 1:
                reconciliation_warnings.append(
                    "All extracted line items are identical; verify the original invoice because the OCR model may have repeated one source row."
                )

        line_sum = (
            None
            if incomplete_line_items
            or not normalized_items
            else sum(
                line_amounts,
                Decimal("0"),
            )
        )

        subtotal = extracted_update[
            "subtotal"
        ]

        tax_rate = extracted_update[
            "tax_rate"
        ]

        tax_amount = extracted_update[
            "tax_amount"
        ]

        discount_amount = extracted_update[
            "discount_amount"
        ]

        total_amount = extracted_update[
            "total_amount"
        ]

        if incomplete_line_items:
            reconciliation_warnings.append(
                "Financial reconciliation requires review because one or more extracted line items are incomplete."
            )

        elif (
            line_sum is not None
            and subtotal is not None
        ):
            if abs(
                line_sum - subtotal
            ) > Decimal("0.01"):
                reconciliation_warnings.append(
                    f"Line-item sum {line_sum:.2f} does not match captured subtotal {subtotal:.2f}."
                )

        if (
            tax_rate is not None
            and tax_amount is not None
            and subtotal is not None
        ):
            expected_tax = (
                subtotal * tax_rate
            ).quantize(
                Decimal("0.01")
            )

            if abs(
                expected_tax - tax_amount
            ) > Decimal("0.01"):
                reconciliation_warnings.append(
                    f"Captured tax {tax_amount:.2f} does not match the captured tax rate calculation {expected_tax:.2f}."
                )

        if (
            subtotal is not None
            and total_amount is not None
        ):
            expected_total = subtotal

            if tax_amount is not None:
                expected_total += tax_amount

            if discount_amount is not None:
                expected_total -= discount_amount

            if (
                tax_amount is None
                or discount_amount is None
            ):
                if abs(
                    total_amount
                    - expected_total
                ) > Decimal("0.01"):
                    missing = []

                    if tax_amount is None:
                        missing.append(
                            "tax"
                        )

                    if discount_amount is None:
                        missing.append(
                            "discount"
                        )

                    reconciliation_warnings.append(
                        "Total cannot be fully reconciled because "
                        + " and ".join(missing)
                        + " value(s) are missing; no missing value was calculated."
                    )

            elif abs(
                total_amount
                - expected_total
            ) > Decimal("0.01"):
                reconciliation_warnings.append(
                    f"Captured total {total_amount:.2f} does not match the independently reconciled total {expected_total:.2f}."
                )

        # =================================================
        # Persist canonical fields
        # =================================================

        await self.document_repository.update(
            document.id,
            extracted_update,
        )

        for key, value in extracted_update.items():
            if hasattr(
                document,
                key,
            ):
                setattr(
                    document,
                    key,
                    value,
                )

        # =================================================
        # Build complete OCR audit payload.
        #
        # IMPORTANT:
        # OCRRepository has create_ocr_result(), not
        # update_ocr_result(). Therefore result is completed
        # here and persisted exactly once.
        # =================================================

        result.key_value_pairs = {
            key: (
                str(value)
                if isinstance(
                    value,
                    Decimal,
                )
                else value
            )
            for key, value in extracted_update.items()
        }

        result.key_value_pairs[
            "line_items"
        ] = [
            {
                key: (
                    str(value)
                    if isinstance(
                        value,
                        Decimal,
                    )
                    else value
                )
                for key, value in item.items()
                if key != "metadata"
            }
            for item in normalized_items
        ]

        result.key_value_pairs[
            "reconciliation"
        ] = {
            "line_item_sum": (
                str(line_sum)
                if line_sum is not None
                else None
            ),
            "subtotal": (
                str(subtotal)
                if subtotal is not None
                else None
            ),
            "tax_rate": (
                str(tax_rate)
                if tax_rate is not None
                else None
            ),
            "tax_amount": (
                str(tax_amount)
                if tax_amount is not None
                else None
            ),
            "discount_amount": (
                str(discount_amount)
                if discount_amount is not None
                else None
            ),
            "total_amount": (
                str(total_amount)
                if total_amount is not None
                else None
            ),
            "warnings": reconciliation_warnings,
        }

        await self.document_repository.replace_document_line_items(
            document_id=document.id,
            org_id=document.org_id,
            items=normalized_items,
        )

        existing_warnings = list(
            getattr(
                document,
                "validation_warnings",
                None,
            )
            or []
        )

        validation_warnings = [
            warning
            for warning in existing_warnings
            if not str(warning).startswith(
                "Financial reconciliation"
            )
            and not str(warning).startswith(
                "Line-item sum"
            )
            and not str(warning).startswith(
                "Captured tax"
            )
            and not str(warning).startswith(
                "Total cannot be fully reconciled"
            )
            and not str(warning).startswith(
                "Captured total"
            )
        ]

        validation_warnings.extend(
            reconciliation_warnings
        )

        await self.document_repository.update(
            document.id,
            {
                "validation_warnings": validation_warnings
            },
        )

        # Persist exactly once using the repository method that actually
        # exists in the current application.
        await self.ocr_repository.create_ocr_result(
            result
        )

        # =================================================
        # Classification
        # =================================================

        await self.document_repository.update_processing_state(
            document.id,
            step="classification",
            message="Identifying the document type and financial workflow",
            progress=72 if not trigger_analysis else 36,
        )
        if not trigger_analysis:
            await self.document_repository.update(document.id, {"capture_progress": 72})

        current_document_type = (
            self._enum_value(
                document.document_type
            )
        )

        current_source = (
            self._enum_value(
                document.source
            )
        )

        classification = None

        try:
            classification = await asyncio.wait_for(
                self.classifier.classify(
                    result.raw_text,
                    document.file_name,
                ),
                timeout=8.0,
            )

        except asyncio.TimeoutError:
            logger.warning(
                "Document classification timed out; using deterministic fallback: document_id=%s",
                document.id,
            )

        except Exception:
            logger.exception(
                "Document classification failed; using deterministic fallback: document_id=%s",
                document.id,
            )

        if (
            not classification
            or classification.get(
                "document_type"
            )
            == DocumentType.UNKNOWN.value
        ):
            classification = (
                self.classifier.classify_rules(
                    result.raw_text,
                    document.file_name,
                )
            )

        if not classification:
            fallback_type = (
                current_document_type
                if current_document_type
                != DocumentType.UNKNOWN.value
                else DocumentType.UNKNOWN.value
            )

            classification = {
                "document_type": fallback_type,
                "confidence": (
                    1.0
                    if fallback_type
                    != DocumentType.UNKNOWN.value
                    else 0.2
                ),
                "reason": (
                    "Used the document type supplied at upload because automatic classification was unavailable."
                    if fallback_type
                    != DocumentType.UNKNOWN.value
                    else "No reliable document signals detected."
                ),
                "source": (
                    "upload_fallback"
                    if fallback_type
                    != DocumentType.UNKNOWN.value
                    else "fallback"
                ),
            }

        detected = str(
            classification.get(
                "document_type"
            )
            or DocumentType.UNKNOWN.value
        )

        if (
            current_document_type
            == DocumentType.UNKNOWN.value
            or current_source == "manual"
        ):
            await self.document_repository.update(
                document.id,
                {
                    "document_type": detected,
                    "classification_confidence": (
                        classification[
                            "confidence"
                        ]
                    ),
                    "classification_reason": (
                        classification[
                            "reason"
                        ]
                    ),
                    "workflow_route": route_for(
                        detected
                    ),
                    "classified_at": (
                        datetime.now(
                            UTC
                        ).isoformat()
                    ),
                },
            )

            document.document_type = (
                DocumentType(
                    detected
                )
            )

        else:
            await self.document_repository.update(
                document.id,
                {
                    "classification_confidence": (
                        classification[
                            "confidence"
                        ]
                    ),
                    "classification_reason": (
                        classification[
                            "reason"
                        ]
                    ),
                    "workflow_route": route_for(
                        current_document_type
                    ),
                    "classified_at": (
                        datetime.now(
                            UTC
                        ).isoformat()
                    ),
                },
            )

        await self.document_repository.update_processing_state(
            document.id,
            step="classification",
            message="Document type identified; moving to financial analysis",
            progress=40,
        )

        # =================================================
        # Personal finance bank statement flow
        # =================================================

        if (
            document.document_type
            == DocumentType.BANK_STATEMENT
        ):
            org = (
                (await execute(get_supabase()
                .table("organizations")
                .select("features")
                .eq(
                    "id",
                    str(document.org_id),
                )
                .single()))
                .data
                or {}
            )

            features = (
                org.get("features")
                or {}
            )

            if (
                features.get(
                    "personal_mode"
                )
                and document.created_by
            ):
                account_id = (
                    document.external_source_data
                    or {}
                ).get(
                    "financial_account_id"
                )

                data = await PersonalExtractor().process(
                    owner_type=OwnerType.PERSONAL,
                    owner_id=document.created_by,
                    document_id=document.id,
                    raw_text=result.raw_text,
                    account_id=(
                        UUID(
                            str(account_id)
                        )
                        if account_id
                        else None
                    ),
                )

                await self.document_repository.update(
                    document.id,
                    {
                        "workflow_route": (
                            "personal_finance"
                        ),
                        "status": "approved",
                        "external_source_data": {
                            **(
                                document.external_source_data
                                or {}
                            ),
                            "statement_import": data,
                        },
                    },
                )

                await self.document_repository.update_pipeline_stage(
                    document.id,
                    PipelineStage.COMPLETE,
                )

                await self.document_repository.update_processing_state(
                    document.id,
                    step="complete",
                    message="Analysis complete — InvoiAI has finished checking this document",
                    progress=100,
                )

                return result

        # =================================================
        # Optional hand-off to full Document Intelligence
        # =================================================
        # OCR/extraction/classification are reusable primitives. AP can call
        # this pipeline in extraction-only mode without silently starting the
        # expensive full AI analysis.
        if not trigger_analysis:
            await self.document_repository.update_document_status(
                document.id,
                DocumentStatus.OCR_COMPLETE,
            )
            await self.document_repository.update_pipeline_stage(
                document.id,
                PipelineStage.OCR,
            )
            await self.document_repository.update_processing_state(
                document.id,
                step="capture_complete",
                message="Document captured and ready for review",
                progress=100,
            )
            await self.document_repository.update(
                document.id,
                {
                    "intelligence_status": "not_requested",
                    "capture_status": "complete",
                    "capture_progress": 100,
                    "capture_error": None,
                },
            )
            return result

        await self.document_repository.update(
            document.id,
            {"intelligence_status": "processing"},
        )

        # =================================================
        # Continue to AI analysis
        # =================================================

        await self.document_repository.update_document_status(
            document.id,
            DocumentStatus.OCR_COMPLETE,
        )

        await self.document_repository.update_pipeline_stage(
            document.id,
            PipelineStage.AI_ANALYSIS,
        )

        await self.document_repository.update_processing_state(
            document.id,
            step="analysis",
            message="Analyzing the financial data and checking for issues",
            progress=42,
        )

        async def _run_analysis() -> None:
            await self.analysis_worker.execute(
                document_id=document.id
            )

            if reconciliation_warnings:
                await self.document_repository.update(
                    document.id,
                    {
                        "status": "needs_review"
                    },
                )

        task = asyncio.create_task(
            _run_analysis(),
            name=f"analysis:{document.id}",
        )

        task.add_done_callback(
            self._log_background_task_failure
        )

        return result

    @staticmethod
    def _log_background_task_failure(
        task: asyncio.Task,
    ) -> None:
        if task.cancelled():
            return

        try:
            task.result()
        except Exception:
            logger.exception(
                "Background analysis task failed"
            )

    # =====================================================
    # Reprocess
    # =====================================================

    async def reprocess(
        self,
        *,
        document_id: UUID,
    ) -> OCRResult:
        """
        Re-run OCR for an existing document.
        """
        return await self.run_ocr(
            document_id=document_id,
        )
