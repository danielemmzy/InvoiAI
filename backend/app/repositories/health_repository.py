from __future__ import annotations

from app.repositories.base import BaseRepository
from app.core.db import execute


class HealthRepository(BaseRepository):
    """Persistence probe used by the application health service."""

    table_name = "organizations"

    async def ping(self) -> bool:
        response = await execute(self.table().select("id").limit(1))
        return bool(response.data is not None)
