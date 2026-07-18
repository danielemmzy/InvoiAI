"""
============================================================
app/repositories/base.py

Base repository shared by all repositories.

Responsibilities:
- Hold the Supabase client
- Shared helper methods
- Common logging

Repositories never contain business logic.
============================================================
"""

import logging

from supabase import Client

from app.core.supabase import get_supabase


logger = logging.getLogger(__name__)


class BaseRepository:
    """
    Base class for every repository.
    """

    def __init__(self) -> None:
        self.db: Client = get_supabase()

    @staticmethod
    def not_found(entity: str) -> ValueError:
        return ValueError(f"{entity} not found")