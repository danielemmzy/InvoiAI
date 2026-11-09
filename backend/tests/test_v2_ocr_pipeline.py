import asyncio
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.enum.database import DocumentType, FileType, PipelineStage
from app.services.ocr.ocr_service import OCRService


@pytest.mark.asyncio
async def test_ocr_pipeline_persists_result_advances_stage_and_triggers_analysis():
    document_id = uuid4()
    org_id = uuid4()
    document = SimpleNamespace(
        id=document_id,
        org_id=org_id,
        file_url="documents/test.pdf",
        file_type=FileType.PDF,
        file_name="test.pdf",
        industry="general",
        document_type=DocumentType.INVOICE,
        source="upload",
        created_by=uuid4(),
        external_source_data={},
        validation_warnings=[],
    )

    class Repo:
        def __init__(self):
            self.stages = []
            self.updates = []
            self.line_items = None

        async def get_document(self, _id):
            return document

        async def update_document_status(self, _id, _status):
            return None

        async def update_processing_state(self, _id, **_kwargs):
            return None

        async def update_pipeline_stage(self, _id, stage):
            self.stages.append(stage)

        async def update(self, _id, payload):
            self.updates.append(payload)

        async def replace_document_line_items(self, **_kwargs):
            self.line_items = _kwargs["items"]

        async def mark_failed(self, *_args, **_kwargs):
            return None

    class Storage:
        async def download_document(self, _url):
            return b"pdf"

    class Provider:
        async def process_document(self, **kwargs):
            assert kwargs["content"] == b"pdf"
            assert kwargs["mime_type"] == "application/pdf"
            return SimpleNamespace(
                raw_text="Hello",
                pages=[SimpleNamespace(page_number=1, text="Hello")],
                tables_detected=[],
                languages=["en"],
                confidence=0.9,
            )

    class Extraction:
        async def extract(self, **_kwargs):
            return None, SimpleNamespace(sections={}, raw_totals={})

        async def compare_ocr_to_image(self, **_kwargs):
            return []

    class Classifier:
        async def classify(self, *_args, **_kwargs):
            return {
                "document_type": DocumentType.INVOICE.value,
                "confidence": 0.95,
                "reason": "Invoice markers found",
            }

    class OCRRepo:
        def __init__(self):
            self.created = None

        async def create_ocr_result(self, result):
            self.created = result
            return result

    class Analysis:
        def __init__(self):
            self.calls = []

        async def execute(self, **kwargs):
            self.calls.append(kwargs)

    repo, ocr_repo, analysis = Repo(), OCRRepo(), Analysis()
    service = OCRService(
        document_repository=repo,
        ocr_repository=ocr_repo,
        storage_service=Storage(),
        provider=Provider(),
        analysis_worker=analysis,
        classifier=Classifier(),
        extraction_service=Extraction(),
    )

    result = await service.run_ocr(document_id=document_id)

    # The background analysis task is intentionally fire-and-forget.
    for _ in range(3):
        await asyncio.sleep(0)

    assert result.raw_text == "Hello"
    assert result.page_count == 1
    assert result.confidence_score == Decimal("0.9")
    assert ocr_repo.created is result
    assert repo.stages == [PipelineStage.OCR, PipelineStage.AI_ANALYSIS]
    assert len(analysis.calls) == 1
    assert analysis.calls[0]["document_id"] == document_id
