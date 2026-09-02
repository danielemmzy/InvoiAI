"""
============================================================
Line Item Service

Business logic for extracted document line items.

Responsibilities
----------------
- Create extracted line items
- Retrieve line items
- Update line items
- Delete line items
- Calculate totals

Repository handles persistence.

No OCR.
No AI.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from app.models.domain.document import DocumentLineItem


class LineItemService:
    """
    Business logic for document line items.
    """

    # =========================================================
    # Create
    # =========================================================

    async def create_items(
        self,
        document_id: UUID,
    ) -> list[DocumentLineItem]:
        """
        Will be implemented after ExtractionService
        begins returning structured line items.
        """
        raise NotImplementedError

    # =========================================================
    # Retrieval
    # =========================================================

    async def get_items(
        self,
        document_id: UUID,
    ) -> list[DocumentLineItem]:
        """
        Repository implementation will be added later.
        """
        raise NotImplementedError

    # =========================================================
    # Update
    # =========================================================

    async def update_item(
        self,
        item_id: UUID,
    ) -> DocumentLineItem:
        raise NotImplementedError

    # =========================================================
    # Delete
    # =========================================================

    async def delete_item(
        self,
        item_id: UUID,
    ) -> None:
        raise NotImplementedError

    # =========================================================
    # Totals
    # =========================================================

    async def calculate_totals(
        self,
        document_id: UUID,
    ):
        """
        Future implementation.

        Used to validate extracted totals.
        """
        raise NotImplementedError