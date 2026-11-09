from decimal import Decimal
from uuid import uuid4

import pytest

from app.services.line_item_service import LineItemService


class FakeLineItemRepository:
    def __init__(self, item=None, items=None, document_exists=True):
        self.item = item
        self.items = items or []
        self.document_exists = document_exists
        self.created = None
        self.updated = None
        self.deleted = None
        self.replaced = None

    async def get_document_line_item(self, *, org_id, item_id):
        return self.item if self.item and self.item["org_id"] == str(org_id) else None

    async def get_document_for_org(self, *, org_id, document_id):
        return {"id": str(document_id), "org_id": str(org_id)}

    async def get_document_for_org(self, *, org_id, document_id):
        return {"id": str(document_id), "org_id": str(org_id)} if self.document_exists else None

    async def create_document_line_items(self, *, org_id, document_id, items):
        self.created = {"org_id": org_id, "document_id": document_id, "items": items}
        return items

    async def list_document_line_items(self, *, org_id, document_id):
        return [item for item in self.items if item["org_id"] == str(org_id) and item["document_id"] == str(document_id)]

    async def update_document_line_item(self, *, org_id, item_id, data):
        self.updated = {"org_id": org_id, "item_id": item_id, "data": data}
        return {**self.item, **data}

    async def delete_document_line_item(self, *, org_id, item_id):
        self.deleted = {"org_id": org_id, "item_id": item_id}
        return True

    async def replace_document_line_items(self, *, org_id, document_id, items):
        self.replaced = {"org_id": org_id, "document_id": document_id, "items": items}
        return items


@pytest.mark.asyncio
async def test_totals_are_decimal_safe_and_scoped_to_the_organization():
    org_id, other_org_id, document_id = uuid4(), uuid4(), uuid4()
    repository = FakeLineItemRepository(items=[
        {"org_id": str(org_id), "document_id": str(document_id), "amount": "0.10", "tax_amount": "0.01", "discount": "0.00"},
        {"org_id": str(org_id), "document_id": str(document_id), "amount": "0.20", "tax_amount": "0.02", "discount": "0.01"},
        {"org_id": str(other_org_id), "document_id": str(document_id), "amount": "900.00", "tax_amount": "0", "discount": "0"},
    ])

    totals = await LineItemService(repository=repository).calculate_totals(org_id=org_id, document_id=document_id)

    assert totals == {
        "line_subtotal": Decimal("0.30"),
        "tax_amount": Decimal("0.03"),
        "discount_amount": Decimal("0.01"),
        "total_amount": Decimal("0.32"),
    }


@pytest.mark.asyncio
async def test_update_preserves_extraction_evidence_and_records_human_correction():
    org_id, document_id, item_id, actor_id = uuid4(), uuid4(), uuid4(), uuid4()
    source_item = {
        "id": str(item_id), "org_id": str(org_id), "document_id": str(document_id),
        "description": "Original OCR description", "quantity": "1", "unit_price": "10.00", "amount": "10.00",
        "metadata": {"extraction_source": "ocr", "confidence": 0.62},
    }
    repository = FakeLineItemRepository(item=source_item)

    updated = await LineItemService(repository=repository).update_item(
        org_id=org_id, item_id=item_id, changes={"description": "Reviewed description", "amount": "12.50"}, actor_id=actor_id
    )

    assert updated["description"] == "Reviewed description"
    assert repository.updated["data"]["metadata"]["extraction_source"] == "ocr"
    correction = repository.updated["data"]["metadata"]["corrections"][-1]
    assert correction["actor_id"] == str(actor_id)
    assert correction["before"] == {"description": "Original OCR description", "amount": "10.00"}
    assert correction["after"] == {"description": "Reviewed description", "amount": "12.50"}


@pytest.mark.asyncio
async def test_delete_rejects_an_item_outside_the_current_organization():
    org_id, other_org_id, item_id = uuid4(), uuid4(), uuid4()
    repository = FakeLineItemRepository(item={"id": str(item_id), "org_id": str(other_org_id), "document_id": str(uuid4())})

    with pytest.raises(ValueError, match="Line item not found"):
        await LineItemService(repository=repository).delete_item(org_id=org_id, item_id=item_id)

    assert repository.deleted is None


def test_rejects_negative_invoice_quantity_and_amount():
    service = LineItemService(repository=FakeLineItemRepository())

    with pytest.raises(ValueError, match="quantity cannot be negative"):
        service._normalize_item({"description": "Credit", "quantity": "-1", "unit_price": "10", "amount": "10"}, position=1)
    with pytest.raises(ValueError, match="amount cannot be negative"):
        service._normalize_item({"description": "Credit", "quantity": "1", "unit_price": "10", "amount": "-10"}, position=1)


@pytest.mark.asyncio
async def test_replace_items_normalizes_all_capture_lines_before_persistence():
    org_id, document_id = uuid4(), uuid4()
    repository = FakeLineItemRepository()

    await LineItemService(repository=repository).replace_items(
        org_id=org_id,
        document_id=document_id,
        items=[{"description": "First", "quantity": 1, "unit_price": "10", "amount": "10"}, {"description": "Second", "quantity": 2, "unit_price": "5", "amount": "10"}],
    )

    assert repository.replaced["org_id"] == org_id
    assert [item["position"] for item in repository.replaced["items"]] == [1, 2]
    assert repository.replaced["items"][0]["amount"] == "10"


def test_normalization_keeps_selected_line_account_as_correction_metadata():
    normalized = LineItemService(repository=FakeLineItemRepository())._normalize_item(
        {"description": "Hosting", "quantity": 1, "unit_price": "10", "amount": "10", "gl_account_id": "account-1", "gl_account_code": "6100", "gl_account_name": "Software"},
        position=1,
    )

    assert normalized["gl_account"] == "6100"
    assert normalized["metadata"]["gl_account_id"] == "account-1"
    assert normalized["metadata"]["gl_account_name"] == "Software"


@pytest.mark.asyncio
async def test_create_rejects_a_document_outside_the_current_organization():
    repository = FakeLineItemRepository(document_exists=False)

    with pytest.raises(ValueError, match="Document not found"):
        await LineItemService(repository=repository).create_items(
            org_id=uuid4(), document_id=uuid4(), items=[{"description": "Paper", "quantity": 1, "unit_price": "10", "amount": "10"}]
        )

    assert repository.created is None
