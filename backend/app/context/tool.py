"""
============================================================
Tool Context

Runtime MCP tool execution context.

Never persisted.
============================================================
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ToolContext(BaseModel):
    """
    MCP tool execution context.
    """

    tool_name: str

    org_id: UUID

    session_id: UUID | None = None

    message_id: UUID | None = None

    request_id: str | None = None

    arguments: dict = Field(default_factory=dict)

    result: dict = Field(default_factory=dict)

    success: bool = True

    latency_ms: int = 0