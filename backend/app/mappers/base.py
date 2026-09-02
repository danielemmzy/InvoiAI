"""
============================================================
Base Mapper

Generic mapper used by all repositories.

Maps between:

PostgreSQL
    ↓
Domain Model
    ↓
Response Schema

The mapper is also the serialization boundary between the
application/domain layer and Supabase/PostgREST.

============================================================
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel


DomainT = TypeVar("DomainT", bound=BaseModel)
ResponseT = TypeVar("ResponseT", bound=BaseModel)


class BaseMapper(
    Generic[
        DomainT,
        ResponseT,
    ]
):
    """
    Base mapper for all domain models.

    Responsibilities:

    1. PostgreSQL row -> Domain model
    2. Domain model -> Response schema
    3. Domain/Pydantic/dict -> JSON-compatible PostgreSQL payload
    4. Supabase response -> normalized row data

    Keeping database serialization here prevents individual
    services and repositories from having to manually convert
    UUIDs, datetimes, enums, decimals, and nested values.
    """

    domain_model: type[DomainT]

    response_model: type[ResponseT]

    # ==========================================================
    # Database -> Domain
    # ==========================================================

    @classmethod
    def to_domain(
        cls,
        row: dict[str, Any] | None,
    ) -> DomainT | None:
        """
        Convert a PostgreSQL/Supabase row into the domain model.
        """

        if row is None:
            return None

        return cls.domain_model.model_validate(row)

    @classmethod
    def to_domain_list(
        cls,
        rows: list[dict[str, Any]] | None,
    ) -> list[DomainT]:
        """
        Convert multiple PostgreSQL/Supabase rows into domain models.
        """

        if not rows:
            return []

        return [
            cls.to_domain(row)
            for row in rows
            if row is not None
        ]

    # ==========================================================
    # Domain -> Response
    # ==========================================================

    @classmethod
    def to_response(
        cls,
        domain: DomainT | None,
    ) -> ResponseT | None:
        """
        Convert a domain model into the API response schema.
        """

        if domain is None:
            return None

        return cls.response_model.model_validate(
            domain.model_dump(
                mode="python",
            )
        )

    @classmethod
    def to_response_list(
        cls,
        domains: list[DomainT] | None,
    ) -> list[ResponseT]:
        """
        Convert multiple domain models into response schemas.
        """

        if not domains:
            return []

        return [
            cls.to_response(domain)
            for domain in domains
            if domain is not None
        ]

    # ==========================================================
    # Domain -> PostgreSQL
    # ==========================================================

    @staticmethod
    def to_insert(
        data: BaseModel | dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert domain input into a JSON-compatible database payload.

        This is the serialization boundary between the application
        domain and Supabase/PostgREST.

        Handles values such as:

        - UUID
        - datetime/date
        - Enum
        - Decimal
        - nested dictionaries
        - nested lists
        - Pydantic models
        """

        if isinstance(data, BaseModel):
            data = data.model_dump(
                mode="python",
                exclude_none=True,
            )

        return jsonable_encoder(data)

    @staticmethod
    def to_update(
        data: BaseModel | dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert update input into a JSON-compatible database payload.

        exclude_unset=True ensures that when a Pydantic model is used
        for partial updates, fields that were not explicitly supplied
        are not accidentally written back to the database.
        """

        if isinstance(data, BaseModel):
            data = data.model_dump(
                mode="python",
                exclude_none=True,
                exclude_unset=True,
            )

        return jsonable_encoder(data)

    # ==========================================================
    # Supabase
    # ==========================================================

    @staticmethod
    def from_supabase(
        response: Any,
    ) -> list[dict[str, Any]]:
        """
        Normalize a Supabase response into a list of row dictionaries.
        """

        if response is None:
            return []

        if hasattr(response, "data"):
            return response.data or []

        return response