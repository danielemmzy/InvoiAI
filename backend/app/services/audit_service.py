"""
============================================================
Audit Service

Writes immutable audit_logs entries.

The repository/model/mapper/schema layers for this already
existed (repositories/audit/audit_repository.py,
models/domain/audit.py, mappers/audit_mapper.py,
schemas/audit.py) but nothing called them — every flow in the
pipeline doc that says "audit_logs INSERT" had nowhere to
route that call. This is the missing thin service layer.

No SQL. No business rules beyond "always write, never update
or delete a log entry" (deletion is exposed on the repository
for admin/GDPR tooling only, not used here).
============================================================
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.repositories.audit.audit_repository import AuditRepository


class AuditService:
    """
    Thin wrapper responsible for writing audit_logs rows.

    Every mutation-producing flow (document upload, approval
    decisions, exports, billing plan changes, member management)
    should call `.log(...)` after the mutation succeeds.
    """

    def __init__(
        self,
        repository: AuditRepository | None = None,
    ) -> None:
        self.repository = repository or AuditRepository()

    async def log(
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
        """
        Writes one audit_logs row.

        `action` should be a dotted, past-tense event name
        matching the pipeline doc's convention, e.g.:
        "document.upload", "document.approved", "document.rejected",
        "document.exported", "document.auto_approved",
        "billing.plan_changed", "member.invited", "member.removed".
        """

        payload = {
            "org_id": org_id,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "old_values": old_values or {},
            "new_values": new_values or {},
            "request_id": request_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        return await self.repository.create_log(payload)

    # ---------------------------------------------------------
    # Convenience helpers for the most common call sites
    # ---------------------------------------------------------

    async def log_document_event(
        self,
        *,
        org_id: UUID,
        user_id: UUID | None,
        action: str,
        document_id: UUID,
        **extra: Any,
    ):
        return await self.log(
            org_id=org_id,
            user_id=user_id,
            action=action,
            resource_type="document",
            resource_id=document_id,
            new_values=extra or None,
        )

    async def list_organization_logs(
        self,
        org_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ):
        return await self.repository.list_organization_logs(
            org_id,
            limit,
            offset,
        )
