"""
============================================================
Base Repository

Shared repository for all persistence operations.

Responsibilities
----------------
- Own the Supabase client
- Standardize CRUD operations
- Convert DB rows -> Domain Models
- Return raw projections when needed
- Keep repositories free of business logic

Repositories should NEVER instantiate domain
models directly. Always use mappers.
============================================================
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar
from uuid import UUID

from supabase import Client

from app.core.supabase import get_supabase
from app.mappers.base import BaseMapper

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository:
    """
    Base class for all repositories.
    """

    table_name: str = ""

    mapper: type[BaseMapper]

    def __init__(self) -> None:

        self.db: Client = get_supabase()

        if not self.table_name:
            raise ValueError(
                f"{self.__class__.__name__} must define table_name."
            )

        if not hasattr(self, "mapper"):
            raise ValueError(
                f"{self.__class__.__name__} must define mapper."
            )

    # =========================================================
    # Helpers
    # =========================================================

    def table(self):
        """
        Returns the Supabase table instance.
        """
        return self.db.table(self.table_name)

    # =========================================================
    # Domain Helpers
    # =========================================================

    def _one(
        self,
        response: Any,
    ) -> T | None:
        """
        Convert a single database row into a domain model.
        """

        data = response.data

        if not data:
            return None

        if isinstance(data, list):
            data = data[0]

        return self.mapper.to_domain(data)

    def _many(
        self,
        response: Any,
    ) -> list[T]:
        """
        Convert multiple database rows into domain models.
        """

        return self.mapper.to_domain_list(
            response.data or [],
        )

    # =========================================================
    # Raw Helpers
    # =========================================================

    @staticmethod
    def raw(
        response: Any,
    ) -> dict[str, Any]:
        """
        Return a single raw database row.
        """

        data = response.data

        if not data:
            return {}

        if isinstance(data, list):
            return data[0]

        return data

    @staticmethod
    def raw_many(
        response: Any,
    ) -> list[dict[str, Any]]:
        """
        Return multiple raw database rows.
        """

        return response.data or []

    # =========================================================
    # CRUD
    # =========================================================

    async def create(
        self,
        data,
    ):

        response = (
            self.table()
            .insert(
                self.mapper.to_insert(data)
            )
            .execute()
        )

        return self._one(response)

    async def get(
        self,
        record_id: UUID,
    ):

        response = (
            self.table()
            .select("*")
            .eq("id", str(record_id))
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def update(
        self,
        record_id: UUID,
        data,
    ):

        response = (
            self.table()
            .update(
                self.mapper.to_update(data)
            )
            .eq("id", str(record_id))
            .execute()
        )

        return self._one(response)

    async def delete(
        self,
        record_id: UUID,
    ) -> bool:

        (
            self.table()
            .delete()
            .eq("id", str(record_id))
            .execute()
        )

        return True

    # =========================================================
    # Queries
    # =========================================================

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        ascending: bool = False,
    ) -> list[T]:

        response = (
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

        return self._many(response)

    async def exists(
        self,
        field: str,
        value: Any,
    ) -> bool:

        if isinstance(value, UUID):
            value = str(value)

        response = (
            self.table()
            .select("id")
            .eq(field, value)
            .limit(1)
            .execute()
        )

        return bool(response.data)

    async def count(
        self,
        **filters,
    ) -> int:

        query = self.table().select(
            "id",
            count="exact",
        )

        for field, value in filters.items():

            if isinstance(value, UUID):
                value = str(value)

            query = query.eq(
                field,
                value,
            )

        response = query.execute()

        return response.count or 0

    # =========================================================
    # Errors
    # =========================================================

    @staticmethod
    def not_found(
        entity: str,
    ) -> ValueError:

        return ValueError(
            f"{entity} not found."
        )