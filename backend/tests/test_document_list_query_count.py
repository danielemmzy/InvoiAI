"""Regression tests for the document-list query plan.

The failure this guards against is query-count growth per document: related
line items, codings, capture data and GL accounts must be fetched once per
page, never once per row.
"""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.context import AuthUser, OrganizationContext
from app.core.enum.database import (
    DocumentSource,
    DocumentStatus,
    DocumentType,
    FileType,
    OrgRole,
    PipelineStage,
    PlanType,
)
from app.core.auth import get_current_user, require_verified_user
from app.core.ocm import get_org_context
from app.core.permissions import VIEW_DOCUMENTS

ORG_ID = UUID("00000000-0000-0000-0000-0000000000aa")
GL_ACCOUNT_ID = UUID("00000000-0000-0000-0000-0000000000bb")


class CountingQuery:
    def __init__(self, database, table_name):
        self.database = database
        self.table_name = table_name
        self.filters = []
        self.wanted_ids = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def in_(self, column, values):
        self.wanted_ids = (column, {str(value) for value in values})
        return self

    def execute(self):
        self.database.executed.append((self.table_name, self.wanted_ids))
        return SimpleNamespace(data=self.database.rows_for(self.table_name, self.wanted_ids))


class CountingDatabase:
    def __init__(self, document_count: int):
        self.executed = []
        self.document_count = document_count
        self.documents = [self._document_row() for _ in range(document_count)]

    def _document_row(self) -> dict:
        document_id = uuid4()
        return {
            "id": str(document_id),
            "org_id": str(ORG_ID),
            "source": DocumentSource.MANUAL.value,
            "document_type": DocumentType.INVOICE.value,
            "industry": "general",
            "file_url": f"org/{document_id}.pdf",
            "file_name": f"{document_id}.pdf",
            "file_type": FileType.PDF.value,
            "pipeline_stage": PipelineStage.INTAKE.value,
            "status": DocumentStatus.PENDING.value,
            "capture_overrides": {"account": {"id": str(GL_ACCOUNT_ID)}},
            "capture_progress": 0,
        }

    def table(self, name):
        return CountingQuery(self, name)

    def rows_for(self, table_name, wanted_ids):
        if table_name == "document_line_items":
            return [
                {"document_id": row["id"], "quantity": 2}
                for row in self.documents
                if wanted_ids is None or row["id"] in wanted_ids[1]
            ]
        if table_name == "invoice_codings":
            return []
        if table_name == "chart_of_accounts":
            return [
                {
                    "id": str(GL_ACCOUNT_ID),
                    "account_code": "5000",
                    "account_name": "Office costs",
                }
            ]
        raise AssertionError(f"Unexpected table queried: {table_name}")


class FakeDocumentRepository:
    def __init__(self, database):
        self.database = database

    async def list_document_rows(self, org_id, limit=50, offset=0, industry=None, query=None):
        # The real implementation returns page rows plus an exact count in one
        # round trip; mirror that shape here.
        self.database.executed.append(("documents", None))
        return self.database.documents[:limit], len(self.database.documents)


def _client_with_fake_backend(monkeypatch, database) -> TestClient:
    from app.main import app
    import app.routers.documents as documents_router

    user = AuthUser(
        id=UUID("00000000-0000-0000-0000-0000000000cc"),
        email="reviewer@example.com",
        org_id=ORG_ID,
        role=OrgRole.OWNER,
        is_verified=True,
    )
    context = OrganizationContext(
        user_id=str(user.id),
        org_id=ORG_ID,
        name="Test Org",
        slug="test-org",
        plan=PlanType.FREE,
        role=OrgRole.OWNER,
        permissions={VIEW_DOCUMENTS},
        document_limit=100,
        default_currency="GBP",
        timezone="Europe/London",
    )
    container = SimpleNamespace(
        document_repository=FakeDocumentRepository(database),
    )

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_verified_user] = lambda: user
    app.dependency_overrides[get_org_context] = lambda: context
    monkeypatch.setattr(documents_router, "get_supabase", lambda: database)
    monkeypatch.setattr(documents_router, "get_container", lambda: container)

    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    from app.main import app

    previous = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


@pytest.mark.parametrize("document_count", [1, 20])
def test_document_list_query_count_does_not_grow_with_page_size(
    monkeypatch, document_count
):
    database = CountingDatabase(document_count)
    client = _client_with_fake_backend(monkeypatch, database)

    response = client.get("/api/v2/documents?offset=0&limit=20")

    assert response.status_code == 200, response.text
    assert len(response.json()) == document_count
    assert response.headers["X-Total-Count"] == str(document_count)

    # Page rows + line items + codings + one batched GL-account lookup.
    # Line items and codings are dispatched together with gather_queries, so
    # their completion order is not deterministic; assert the multiset.
    ids = {row["id"] for row in database.documents}
    assert database.executed[0] == ("documents", None)
    assert sorted(database.executed[1:3], key=lambda item: item[0]) == [
        ("document_line_items", ("document_id", ids)),
        ("invoice_codings", ("document_id", ids)),
    ]
    assert database.executed[3] == ("chart_of_accounts", ("id", {str(GL_ACCOUNT_ID)}))
    assert len(database.executed) == 4


def test_document_list_constant_query_count_across_sizes(monkeypatch):
    counts = []
    for document_count in (1, 20, 60):
        database = CountingDatabase(document_count)
        client = _client_with_fake_backend(monkeypatch, database)
        response = client.get("/api/v2/documents?offset=0&limit=20")
        assert response.status_code == 200, response.text
        counts.append(len(database.executed))

    assert counts == [4, 4, 4]
