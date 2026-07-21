"""
============================================================
Audit Repository

Responsible ONLY for audit log persistence.

No business logic.
No authorization.
No logging decisions.
============================================================
"""

from typing import Any
from unittest import result

from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository):

    TABLE = "audit_logs"

    def logs(self):
        return self.db.table(self.TABLE)

        # =========================================================

    # Create
    # =========================================================

    async def create(
        self,
        values: dict[str, Any],
    ) -> dict:
        """
        Persist an audit record.
        """

        result = self.logs().insert(values).execute()

        return result.data[0]

        # =========================================================

    # Get
    # =========================================================

    async def get(
        self,
        audit_id: str,
    ) -> dict | None:

        result = self.logs().select("*").eq("id", audit_id).limit(1).execute()

        return result.data[0] if result.data else None

    async def exists(
        self,
        audit_id: str,
    ) -> bool:

        result = self.logs().select("id").eq("id", audit_id).limit(1).execute()

        return bool(result.data)

    async def list_org_logs(
        self,
        org_id: str,
        limit: int = 100,
    ) -> list[dict]:

        result = (
            self.logs()
            .select("*")
            .eq("org_id", org_id)
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []
    
    async def list_user_logs(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[dict]:

        result = (
            self.logs()
            .select("*")
            .eq("user_id", user_id)
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []
    
    async def list_action_logs(
        self,
        org_id: str,
        action: str,
        limit: int = 100,
    ) -> list[dict]:

        result = (
            self.logs()
            .select("*")
            .eq("org_id", org_id)
            .eq("action", action)
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []
    
    async def list_resource_logs(
        self,
        org_id: str,
        resource_type: str,
        resource_id: str,
    ) -> list[dict]:

        result = (
            self.logs()
            .select("*")
            .eq("org_id", org_id)
            .eq("resource_type", resource_type)
            .eq("resource_id", resource_id)
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return result.data or []
    
    async def list_request_logs(
        self,
        request_id: str,
    ) -> list[dict]:

        result = (
            self.logs()
            .select("*")
            .eq("request_id", request_id)
            .order(
                "created_at",
                desc=False,
            )
            .execute()
        )

        return result.data or []
