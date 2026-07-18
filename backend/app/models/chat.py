# ============================================================
# app/models/chat.py
#
# Finance Copilot models
#
# Supports:
# - Chat sessions
# - Chat messages
# - AI tool calls
# - RAG citations
# - Multi-provider AI
# ============================================================

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.enums import ChatRole


# ============================================================
# Chat Session
# ============================================================

class ChatSessionCreate(BaseModel):
    """
    Start a new Finance Copilot conversation.
    """

    title: Optional[str] = Field(
        default="New Chat",
        max_length=200,
    )


class ChatSessionUpdate(BaseModel):

    title: Optional[str] = Field(
        None,
        max_length=200,
    )

    archived: Optional[bool] = None


class ChatSession(BaseModel):

    id: str

    org_id: str

    created_by: str

    title: str

    archived: bool

    created_at: Optional[datetime]

    updated_at: Optional[datetime]


# ============================================================
# Chat Message
# ============================================================

class ChatMessageCreate(BaseModel):

    message: str = Field(
        ...,
        min_length=1,
    )


class ChatMessage(BaseModel):

    id: str

    session_id: str

    role: ChatRole

    message: str

    model: Optional[str]

    tokens_used: Optional[int]

    response_time_ms: Optional[int]

    created_at: Optional[datetime]


# ============================================================
# Tool Calls
# ============================================================

class ToolCall(BaseModel):

    id: str

    message_id: str

    tool_name: str

    arguments: dict[str, Any]

    result: Optional[dict[str, Any]]

    success: bool

    execution_ms: Optional[int]

    created_at: Optional[datetime]


# ============================================================
# Citations
# ============================================================

class ChatCitation(BaseModel):

    document_id: str

    page: Optional[int]

    confidence: float

    snippet: Optional[str]


# ============================================================
# AI Response
# ============================================================

class ChatResponse(BaseModel):

    session_id: str

    message: ChatMessage

    citations: list[ChatCitation] = []

    tool_calls: list[ToolCall] = []

    suggested_questions: list[str] = []


# ============================================================
# Chat Summary
# ============================================================

class ChatSummary(BaseModel):

    id: str

    title: str

    last_message: Optional[str]

    last_activity: Optional[datetime]

    message_count: int


# ============================================================
# Chat Page
# ============================================================

class ChatPage(BaseModel):

    sessions: list[ChatSummary]

    count: int

    offset: int

    limit: int