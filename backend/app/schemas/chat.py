from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

"""
============================================================
Chat Schemas

API request/response models.

- chat_sessions
- chat_messages
- tool_calls
============================================================
"""


# ============================================================
# Send Message
# ============================================================

class ChatMessageCreate(BaseModel):

    content: str


# ============================================================
# Chat Session Response
# ============================================================

class ChatSessionResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    org_id: UUID

    user_id: UUID

    title: str | None

    is_active: bool

    document_ids: list[UUID]

    vendor_ids: list[UUID]

    total_messages: int

    total_tokens: int

    total_cost_usd: Decimal

    metadata: dict[str, Any]

    created_at: datetime

    updated_at: datetime


# ============================================================
# Chat Message Response
# ============================================================

class ChatMessageResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    session_id: UUID

    org_id: UUID

    user_id: UUID

    role: str

    content: str

    context_used: dict[str, Any]

    retrieved_docs: dict[str, Any]

    retrieved_vendors: dict[str, Any]

    tokens_used: int

    model_used: str

    latency_ms: int

    cost_usd: Decimal

    created_at: datetime


# ============================================================
# Tool Call Response
# ============================================================

class ToolCallResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    message_id: UUID

    session_id: UUID

    org_id: UUID

    tool_name: str

    tool_input: dict[str, Any]

    tool_output: dict[str, Any]

    success: bool

    error: str | None

    latency_ms: int

    created_at: datetime


# ============================================================
# Lists
# ============================================================

class ChatSessionListResponse(BaseModel):

    items: list[ChatSessionResponse] = Field(default_factory=list)

    total: int


class ChatMessageListResponse(BaseModel):

    items: list[ChatMessageResponse] = Field(default_factory=list)

    total: int


class ToolCallListResponse(BaseModel):

    items: list[ToolCallResponse] = Field(default_factory=list)

    total: int