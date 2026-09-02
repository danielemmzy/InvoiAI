"""
============================================================
Authentication Context

Request-scoped authentication information.

This object is created after successful authentication
and passed through the service layer.

It is never persisted.

============================================================
"""

from uuid import UUID

from pydantic import BaseModel, Field


from app.core.enum.database import OrgRole


class AuthContext(BaseModel):
    """
    Current authenticated user.
    """

    user_id: UUID

    org_id: UUID

    role: OrgRole

    email: str

    is_authenticated: bool = True

    is_superuser: bool = False

    permissions: list[str] = Field(default_factory=list)

    session_id: str | None = None

    access_token: str | None = None

class AuthUser(BaseModel):
    """
    Current authenticated user.
    """

    id: UUID

    email: str

    org_id: UUID | None = None

    role: OrgRole | None = None

    is_active: bool = True

    is_verified: bool = True

    # Kept for compatibility with the remaining V1-facing routers
    # while the application migrates to organization-scoped V2
    # authorization. The authoritative subscription/plan source
    # should ultimately be the V2 profile/billing service.
    plan: str = "free"

    permissions: set[str] = Field(default_factory=set)