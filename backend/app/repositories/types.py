"""
============================================================
app/repositories/types.py

Shared repository types.

These classes standardize pagination, sorting,
filtering and paged responses across repositories.

Repositories should use these instead of defining
their own pagination structures.
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ============================================================
# Pagination
# ============================================================

@dataclass(slots=True)
class Pagination:
    """
    Pagination parameters.
    """

    limit: int = 50
    offset: int = 0


# ============================================================
# Sorting
# ============================================================

@dataclass(slots=True)
class Sort:
    """
    Sorting options.
    """

    field: str = "created_at"
    ascending: bool = False


# ============================================================
# Search
# ============================================================

@dataclass(slots=True)
class Search:
    """
    Text search.
    """

    query: str


# ============================================================
# Repository Page
# ============================================================

@dataclass(slots=True)
class Page:
    """
    Standard paginated result.
    """

    items: list[Any]
    total: int
    limit: int
    offset: int