"""AP and Document Intelligence must not overwrite each other's progress.

Both phases share ``documents.processing_step/message/progress``. Once an
invoice enters AP, the AP page is the source of truth; an OCR or analysis pass
must not replace it with an older phase's label.
"""

from types import SimpleNamespace
from uuid import UUID

import pytest

from app.repositories.document.document_repository import (
    DocumentRepository,
    should_write_processing_state,
)

DOC = UUID("00000000-0000-0000-0000-000000000003")


def test_di_progress_is_allowed_before_ap_owns_the_document():
    for status in (None, "", "received", "extracting"):
        assert should_write_processing_state(
            ap_enabled=True, ap_status=status, step="analysis"
        )
    assert should_write_processing_state(
        ap_enabled=False, ap_status="coding", step="analysis"
    )


def test_di_progress_is_blocked_once_ap_owns_the_document():
    for status in ("validating", "matching", "coding", "coding_exception", "approved"):
        assert not should_write_processing_state(
            ap_enabled=True, ap_status=status, step="analysis"
        )


def test_ap_steps_are_always_allowed():
    assert should_write_processing_state(
        ap_enabled=True, ap_status="coding", step="ap_coding"
    )
    assert should_write_processing_state(
        ap_enabled=False, ap_status="coding", step="ap_validating"
    )


class _Query:
    def __init__(self, db):
        self.db = db
        self._update = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def update(self, payload):
        self._update = payload
        self.db.updates.append(payload)
        return self

    def execute(self):
        if self._update is not None:
            return SimpleNamespace(data=[])
        return SimpleNamespace(
            data=[
                {
                    "ap_enabled": self.db.ap_enabled,
                    "ap_status": self.db.ap_status,
                }
            ]
        )


class _FakeDb:
    def __init__(self, *, ap_enabled: bool, ap_status: str | None):
        self.ap_enabled = ap_enabled
        self.ap_status = ap_status
        self.updates: list[dict] = []

    def table(self, _name):
        return _Query(self)


def _repository(db) -> DocumentRepository:
    repository = DocumentRepository()
    repository.db = db
    return repository


@pytest.mark.asyncio
async def test_analysis_cannot_replace_ap_progress_at_coding():
    db = _FakeDb(ap_enabled=True, ap_status="coding")
    repository = _repository(db)

    await repository.update_processing_state(
        DOC,
        step="analysis",
        message="Running document analysis",
        progress=25,
    )

    assert db.updates == []


@pytest.mark.asyncio
async def test_ap_step_can_write_progress_at_coding():
    db = _FakeDb(ap_enabled=True, ap_status="coding")
    repository = _repository(db)

    await repository.update_processing_state(
        DOC,
        step="ap_coding",
        message="Assigning GL accounts",
        progress=70,
    )

    assert db.updates == [
        {
            "processing_step": "ap_coding",
            "processing_message": "Assigning GL accounts",
            "processing_progress": 70,
        }
    ]


@pytest.mark.asyncio
async def test_di_step_still_writes_before_ap_starts():
    db = _FakeDb(ap_enabled=False, ap_status=None)
    repository = _repository(db)

    await repository.update_processing_state(
        DOC,
        step="analysis",
        message="Running document analysis",
        progress=25,
    )

    assert len(db.updates) == 1
