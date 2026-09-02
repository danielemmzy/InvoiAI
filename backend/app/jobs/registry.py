from __future__ import annotations

from typing import Type

from app.jobs.base import BaseJob


class JobRegistry:
    """
    Global Job Registry.

    Responsibilities
    ----------------
    • Register available jobs
    • Resolve jobs by name
    • Prevent duplicate registrations

    This registry is independent of
    Redis/Celery/RQ.

    Workers, schedulers and queues
    all use this registry.
    """

    def __init__(self) -> None:

        self._jobs: dict[str, Type[BaseJob]] = {}

    # =====================================================
    # Register
    # =====================================================

    def register(
        self,
        job: Type[BaseJob],
    ) -> None:

        name = job.__name__

        if name in self._jobs:

            raise ValueError(
                f"Job '{name}' already registered."
            )

        self._jobs[name] = job

    # =====================================================
    # Resolve
    # =====================================================

    def resolve(
        self,
        name: str,
    ) -> Type[BaseJob]:

        if name not in self._jobs:

            raise KeyError(
                f"Unknown job '{name}'."
            )

        return self._jobs[name]

    # =====================================================
    # Exists
    # =====================================================

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self._jobs

    # =====================================================
    # List
    # =====================================================

    def list(
        self,
    ) -> list[str]:

        return sorted(
            self._jobs.keys(),
        )

    # =====================================================
    # Remove
    # =====================================================

    def unregister(
        self,
        name: str,
    ) -> None:

        self._jobs.pop(
            name,
            None,
        )

    # =====================================================
    # Clear
    # =====================================================

    def clear(
        self,
    ) -> None:

        self._jobs.clear()


#
# Global registry instance
#

job_registry = JobRegistry()