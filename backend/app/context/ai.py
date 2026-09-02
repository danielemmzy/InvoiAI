"""
============================================================
AI Context

Runtime AI execution context.

Carries all AI execution configuration for a
single request.

Never persisted.
============================================================
"""

from decimal import Decimal

from pydantic import BaseModel


class AIContext(BaseModel):
    """
    Runtime AI context.
    """

    model: str

    provider: str

    prompt_version: str

    engine_version: str | None = None

    temperature: Decimal = Decimal("0")

    max_tokens: int | None = None

    embedding_model: str | None = None

    request_id: str | None = None

    estimated_cost_usd: Decimal = Decimal("0")

    tokens_used: int = 0

    processing_ms: int = 0