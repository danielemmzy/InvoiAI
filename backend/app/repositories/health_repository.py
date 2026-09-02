from __future__ import annotations

from app.repositories.base import BaseRepository


class HealthRepository(BaseRepository):
    """Persistence probe used by the application health service."""

    table_name = "organizations"

    async def ping(self) -> bool:
        response = self.table().select("id").limit(1).execute()
        return bool(response.data is not None)
