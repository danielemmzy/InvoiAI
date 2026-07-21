"""
============================================================
app/repositories/document/vendor_repository.py

Vendor repository.

Responsible ONLY for vendor persistence.

No AI.
No OCR.
No business logic.

Business logic belongs inside VendorService.
============================================================
"""

from __future__ import annotations

from typing import Any

from app.repositories.base import BaseRepository



class VendorRepository(BaseRepository):

    def __init__(self, db: Any):
        super().__init__(
            db=db,
            table_name="vendors",
        )

    # =========================================================
    # Lookups
    # =========================================================

    async def get_by_name(
        self,
        org_id: str,
        name: str,
    ):
        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .ilike("name", name)
            .limit(1)
            .execute()
        )

    async def get_by_email(
        self,
        org_id: str,
        email: str,
    ):
        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("email", email)
            .limit(1)
            .execute()
        )

    async def get_by_tax_id(
        self,
        org_id: str,
        tax_id: str,
    ):
        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("tax_id", tax_id)
            .limit(1)
            .execute()
        )

    # =========================================================
    # Search
    # =========================================================

    async def search(
        self,
        org_id: str,
        query: str,
        limit: int = 20,
    ):
        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .ilike("name", f"%{query}%")
            .limit(limit)
            .execute()
        )

    # =========================================================
    # Preferred
    # =========================================================

    async def list_preferred(
        self,
        org_id: str,
    ):
        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("is_preferred", True)
            .execute()
        )

    # =========================================================
    # Blocked
    # =========================================================

    async def list_blocked(
        self,
        org_id: str,
    ):
        return (
            self.table()
            .select("*")
            .eq("org_id", org_id)
            .eq("is_blocked", True)
            .execute()
        )

    async def set_preferred(
        self,
        vendor_id: str,
        preferred: bool,
    ):
        return await self.update(
            vendor_id,
            {
                "is_preferred": preferred,
            },
        )

    async def block(
        self,
        vendor_id: str,
        reason: str,
    ):
        return await self.update(
            vendor_id,
            {
                "is_blocked": True,
                "blocked_reason": reason,
            },
        )

    async def unblock(
        self,
        vendor_id: str,
    ):
        return await self.update(
            vendor_id,
            {
                "is_blocked": False,
                "blocked_reason": None,
            },
        )

    # =========================================================
    # Statistics
    # =========================================================

    async def get_statistics(
        self,
        vendor_id: str,
    ):
        return (
            self.table()
            .select(
                """
                invoice_count,
                receipt_count,
                total_document_count,
                total_spend,
                average_spend,
                risk_score,
                risk_level
                """
            )
            .eq("id", vendor_id)
            .single()
            .execute()
        )

    async def get_financial_summary(
        self,
        vendor_id: str,
    ):
        return (
            self.table()
            .select("*")
            .eq("id", vendor_id)
            .single()
            .execute()
        )