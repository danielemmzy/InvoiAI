"""
============================================================
Execution Context

Shared runtime context.

Combines authentication, organization,
request and execution metadata into
a single object passed across services.

Never persisted.
============================================================
"""

from pydantic import BaseModel

from app.context.auth import AuthContext
from app.context.organization import OrganizationContext
from app.context.request import RequestContext


class ExecutionContext(BaseModel):
    """
    Runtime execution context.
    """

    auth: AuthContext

    organization: OrganizationContext

    request: RequestContext

    background_job: bool = False

    ai_request: bool = False

    integration_request: bool = False

    dry_run: bool = False

    trace_enabled: bool = True