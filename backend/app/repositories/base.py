"""
============================================================
app/repositories/base_repository.py

Base repository for all persistence operations.

Responsibilities
----------------
- Hold the shared Supabase client
- Provide reusable CRUD helpers
- Standardize pagination
- Standardize existence checks
- Standardize count operations

Repositories should NEVER contain business logic.
Business rules belong in the service layer.
============================================================
"""

from __future__ import annotations

import logging
from typing import Any

from supabase import Client

from app.core.supabase import get_supabase

logger = logging.getLogger(__name__)


class BaseRepository:
    """
    Base class for all repositories.
    """

    table_name: str = ""

    def __init__(self) -> None:
        self.db: Client = get_supabase()

        if not self.table_name:
            raise ValueError(
                f"{self.__class__.__name__} must define table_name."
            )

    # =========================================================
    # Internal helper
    # =========================================================

    def table(self):
        """
        Returns the Supabase table instance.
        """
        return self.db.table(self.table_name)

    # =========================================================
    # Generic CRUD
    # =========================================================

    async def create(self, data: dict):
        return (
            self.table()
            .insert(data)
            .execute()
        )

    async def get(self, record_id: str):
        return (
            self.table()
            .select("*")
            .eq("id", record_id)
            .single()
            .execute()
        )

    async def update(
        self,
        record_id: str,
        data: dict,
    ):
        return (
            self.table()
            .update(data)
            .eq("id", record_id)
            .execute()
        )

    async def delete(self, record_id: str):
        return (
            self.table()
            .delete()
            .eq("id", record_id)
            .execute()
        )

    # =========================================================
    # Common Queries
    # =========================================================

    async def exists(
        self,
        field: str,
        value: Any,
    ) -> bool:

        result = (
            self.table()
            .select("id")
            .eq(field, value)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def count(self) -> int:

        result = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .execute()
        )

        return result.count or 0

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        ascending: bool = False,
    ):
        return (
            self.table()
            .select("*")
            .order(
                order_by,
                desc=not ascending,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

    # =========================================================
    # Helpers
    # =========================================================

    @staticmethod
    def not_found(entity: str) -> ValueError:
        return ValueError(f"{entity} not found")