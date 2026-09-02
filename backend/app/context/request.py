"""
============================================================
Request Context

Request-scoped HTTP information.

Carries metadata about the current request through
the application.

Never persisted.
============================================================
"""

from pydantic import BaseModel


class RequestContext(BaseModel):
    """
    Current HTTP request context.
    """

    request_id: str

    correlation_id: str

    method: str

    path: str

    client_ip: str | None = None

    user_agent: str | None = None

    browser: str | None = None

    device_type: str | None = None

    operating_system: str | None = None

    country: str | None = None

    city: str | None = None