from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Generic
from typing import TypeVar

from app.integrations.base.exceptions import MappingError

T = TypeVar("T")


class BaseIntegrationMapper(
    ABC,
    Generic[T],
):
    """
    Base mapper for external providers.

    Responsibilities
    ----------------
    • Convert provider payloads
      into domain models.

    No persistence.

    No API calls.

    No business logic.
    """

    @abstractmethod
    def to_domain(
        self,
        payload: dict,
    ) -> T:
        """
        Convert provider payload
        into domain model.
        """

    @abstractmethod
    def to_provider(
        self,
        model: T,
    ) -> dict:
        """
        Convert domain model
        into provider payload.
        """

    def require(
        self,
        payload: dict,
        field: str,
    ):
        """
        Ensure a required field exists.
        """

        value = payload.get(field)

        if value is None:

            raise MappingError(
                f"Missing required field '{field}'."
            )

        return value

    def optional(
        self,
        payload: dict,
        field: str,
        default=None,
    ):
        """
        Read optional field.
        """

        return payload.get(
            field,
            default,
        )