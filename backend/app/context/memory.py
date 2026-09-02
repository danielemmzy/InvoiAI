"""
============================================================
Memory Context

Runtime RAG / memory context.

Never persisted.
============================================================
"""

from uuid import UUID

from pydantic import BaseModel, Field


class MemoryContext(BaseModel):
    """
    Runtime memory context.
    """

    org_id: UUID

    document_id: UUID | None = None

    vendor_id: UUID | None = None

    chat_session_id: UUID | None = None

    retrieved_documents: list[UUID] = Field(default_factory=list)

    retrieved_vendors: list[UUID] = Field(default_factory=list)

    retrieved_memories: list[str] = Field(default_factory=list)

    embedding_model: str | None = None

    max_results: int = 10