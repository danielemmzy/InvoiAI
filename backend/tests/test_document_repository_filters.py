from uuid import uuid4

import pytest

from app.repositories.document.document_repository import DocumentRepository


class FakeResponse:
    data = []


class FakeQuery:
    def __init__(self):
        self.filters = []

    def select(self, *_args, **_kwargs): return self
    def eq(self, field, value): self.filters.append((field, value)); return self
    def or_(self, expression): self.filters.append(("or", expression)); return self
    def order(self, *_args, **_kwargs): return self
    def range(self, *_args, **_kwargs): return self
    def execute(self): return FakeResponse()


@pytest.mark.asyncio
async def test_list_documents_applies_industry_with_organization_scope():
    query = FakeQuery()
    repository = object.__new__(DocumentRepository)
    repository.table = lambda: query
    repository._many = lambda response: response.data

    await repository.list_documents(uuid4(), industry="construction")

    assert ("industry", "construction") in query.filters


@pytest.mark.asyncio
async def test_list_documents_scopes_invoice_or_vendor_search_to_the_organization():
    query = FakeQuery()
    repository = object.__new__(DocumentRepository)
    repository.table = lambda: query
    repository._many = lambda response: response.data

    await repository.list_documents(uuid4(), query="INV-2048")

    assert ("or", "document_number.ilike.*INV-2048*,vendor_name.ilike.*INV-2048*") in query.filters


@pytest.mark.asyncio
async def test_list_documents_rejects_postgrest_search_syntax():
    repository = object.__new__(DocumentRepository)

    with pytest.raises(ValueError, match="unsupported filter syntax"):
        await repository.list_documents(uuid4(), query="invoice,org_id.eq.other-org")
