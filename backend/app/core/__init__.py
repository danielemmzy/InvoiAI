"""
============================================================
Chat Domain Models

Mirror PostgreSQL tables.

- chat_sessions
- chat_messages
- tool_calls
============================================================
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enum.application import ChatRole
from app.models.domain.base import DomainModel


# ============================================================
# Chat Session
# ============================================================

class ChatSession(DomainModel):
    """
    Mirrors chat_sessions.
    """

    id: UUID

    org_id: UUID

    user_id: UUID

    title: str

    is_active: bool

    document_ids: list[UUID] = Field(default_factory=list)

    vendor_ids: list[UUID] = Field(default_factory=list)

    total_messages: int

    total_tokens: int

    total_cost_usd: Decimal

    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: Any

    updated_at: Any


# ============================================================
# Chat Message
# ============================================================

class ChatMessage(DomainModel):
    """
    Mirrors chat_messages.
    """

    id: UUID

    session_id: UUID

    org_id: UUID

    user_id: UUID

    role: ChatRole

    content: str

    context_used: dict[str, Any] = Field(default_factory=dict)

    retrieved_docs: dict[str, Any] = Field(default_factory=dict)

    retrieved_vendors: dict[str, Any] = Field(default_factory=dict)

    tokens_used: int

    model_used: str | None = None

    latency_ms: int | None = None

    cost_usd: Decimal | None = None

    created_at: Any


# ============================================================
# Tool Call
# ============================================================

class ToolCall(DomainModel):
    """
    Mirrors tool_calls.
    """

    id: UUID

    message_id: UUID

    session_id: UUID

    org_id: UUID

    tool_name: str

    tool_input: dict[str, Any] = Field(default_factory=dict)

    tool_output: dict[str, Any] = Field(default_factory=dict)

    success: bool

    error: str | None = None

    latency_ms: int | None = None

    created_at: Any