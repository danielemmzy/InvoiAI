from __future__ import annotations

from uuid import UUID

from app.mappers.audit_mapper import AuditLogMapper
from app.models.domain.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    """
    Repository for audit_logs.
    """

    table_name = "audit_logs"
    mapper = AuditLogMapper

    async def create_log(
        self,
        log: AuditLog | dict,
    ) -> AuditLog | None:
        return await self.create(log)

    async def get_log(
        self,
        log_id: UUID,
    ) -> AuditLog | None:
        return await self.get(log_id)

    async def delete_log(
        self,
        log_id: UUID,
    ) -> bool:
        return await self.delete(log_id)

    async def list_organization_logs(
        self,
        org_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return self._many(response)

    async def list_user_logs(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:

        response = (
            self.table()
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return self._many(response)

    async def list_resource_logs(
        self,
        resource_type: str,
        resource_id: UUID,
    ) -> list[AuditLog]:

        response = (
            self.table()
            .select("*")
            .eq("resource_type", resource_type)
            .eq("resource_id", str(resource_id))
            .order("created_at", desc=True)
            .execute()
        )

        return self._many(response)

    async def list_request_logs(
        self,
        request_id: str,
    ) -> list[AuditLog]:

        response = (
            self.table()
            .select("*")
            .eq("request_id", request_id)
            .order("created_at")
            .execute()
        )

        return self._many(response)