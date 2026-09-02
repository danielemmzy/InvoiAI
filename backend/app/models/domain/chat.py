"""
============================================================
Chat Domain Models

Mirror PostgreSQL tables.

- chat_sessions
- chat_messages
- tool_calls

Repositories return these models only.
============================================================
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.domain.base import DomainModel


JsonDict = dict[str, Any]


# ============================================================
# Chat Session
# ============================================================

class ChatSession(DomainModel):
    """
    Mirrors chat_sessions table.
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

    metadata: JsonDict = Field(default_factory=dict)

    created_at: datetime

    updated_at: datetime


# ============================================================
# Chat Message
# ============================================================

class ChatMessage(DomainModel):
    """
    Mirrors chat_messages table.
    """

    id: UUID

    session_id: UUID

    org_id: UUID

    user_id: UUID

    role: str

    content: str

    context_used: JsonDict = Field(default_factory=dict)

    retrieved_docs: JsonDict = Field(default_factory=dict)

    retrieved_vendors: JsonDict = Field(default_factory=dict)

    tokens_used: int

    model_used: str

    latency_ms: int

    cost_usd: Decimal

    created_at: datetime


# ============================================================
# Tool Call
# ============================================================

class ToolCall(DomainModel):
    """
    Mirrors tool_calls table.
    """

    id: UUID

    message_id: UUID

    session_id: UUID

    org_id: UUID

    tool_name: str

    tool_input: JsonDict = Field(default_factory=dict)

    tool_output: JsonDict = Field(default_factory=dict)

    success: bool

    error: str | None = None

    latency_ms: int

    created_at: datetime