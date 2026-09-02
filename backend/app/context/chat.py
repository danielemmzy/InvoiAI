"""
============================================================
Chat Context

Runtime chat/copilot context.

Never persisted.
============================================================
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ChatContext(BaseModel):
    """
    Current chat session.
    """

    session_id: UUID

    org_id: UUID

    user_id: UUID

    message_id: UUID | None = None

    title: str | None = None

    retrieved_document_ids: list[UUID] = Field(default_factory=list)

    retrieved_vendor_ids: list[UUID] = Field(default_factory=list)

    total_tokens: int = 0

    total_cost_usd: float = 0

    model: str | None = None