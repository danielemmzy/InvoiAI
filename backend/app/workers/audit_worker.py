from __future__ import annotations

from typing import Any
from uuid import UUID

from app.services.audit_service import AuditService
from app.workers.base import BaseWorker


class AuditWorker(BaseWorker):
    """Durable orchestration boundary for asynchronous audit writes.

    The worker is event-driven rather than cron-driven. It should receive
    immutable audit events from the application job queue when audit writes
    must be decoupled from the request path.
    """

    def __init__(self, *, audit_service: AuditService) -> None:
        super().__init__()
        self.audit_service = audit_service

    async def run(
        self,
        *,
        org_id: UUID,
        user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        return await self.audit_service.log(
            org_id=org_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
