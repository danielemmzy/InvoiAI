import pytest
from types import SimpleNamespace
from uuid import uuid4
from decimal import Decimal

from app2.services.ocr.ocr_service import OCRService


@pytest.mark.asyncio
async def test_ocr_pipeline_persists_result_advances_stage_and_triggers_analysis():
    document_id = uuid4()
    org_id = uuid4()
    document = SimpleNamespace(
        id=document_id,
        org_id=org_id,
        file_url="documents/test.pdf",
        file_type=SimpleNamespace(value="application/pdf"),
    )

    segment = SimpleNamespace(start_index=0, end_index=5)
    page = SimpleNamespace(
        layout=SimpleNamespace(
            text_anchor=SimpleNamespace(text_segments=[segment]),
            confidence=0.9,
        ),
        tables=[],
        detected_languages=[SimpleNamespace(language_code="en")],
    )
    google_result = SimpleNamespace(text="Hello", pages=[page])

    class Repo:
        def __init__(self):
            self.stages = []
            self.ocr = None
        async def get_document(self, _id):
            return document
        async def update_pipeline_stage(self, _id, stage):
            self.stages.append(stage)
        async def create_ocr_result(self, result):
            self.ocr = result

    class Storage:
        async def download_document(self, _url):
            return b"pdf"

    class Provider:
        def process_document(self, **kwargs):
            assert kwargs["content"] == b"pdf"
            return google_result

    class Analysis:
        def __init__(self):
            self.calls = []
        async def execute(self, **kwargs):
            self.calls.append(kwargs)

    repo, analysis = Repo(), Analysis()
    service = OCRService(
        document_repository=repo,
        storage_service=Storage(),
        provider=Provider(),
        analysis_worker=analysis,
    )

    result = await service.run_ocr(document_id=document_id)

    assert result.raw_text == "Hello"
    assert result.page_count == 1
    assert result.confidence_score == Decimal("0.9")
    assert repo.ocr is result
    assert len(repo.stages) == 2
    assert len(analysis.calls) == 1
    assert analysis.calls[0]["document_id"] == document_id
