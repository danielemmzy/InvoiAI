"""
============================================================
Conversation Builder

Responsible for constructing conversation history
sent to the LLM.

Responsibilities
----------------
- Convert chat history to OpenAI format
- Keep ordering consistent
- Limit conversation length

No repositories.

No OpenAI calls.

No business logic.
============================================================
"""

from __future__ import annotations

from app.models.domain.chat import ChatMessage


class ConversationBuilder:
    """
    Builds conversation history for GPT.
    """

    DEFAULT_LIMIT = 20

    # =====================================================
    # Build History
    # =====================================================

    @classmethod
    def build(
        cls,
        *,
        history: list[ChatMessage],
    ) -> list[dict]:
        """
        Converts stored chat messages into the format
        expected by OpenAI.
        """

        messages: list[dict] = []

        for item in history:

            messages.append(
                {
                    "role": item.role,
                    "content": item.content,
                }
            )

        return messages

    # =====================================================
    # Limit History
    # =====================================================

    @classmethod
    def trim(
        cls,
        *,
        history: list[ChatMessage],
        limit: int | None = None,
    ) -> list[ChatMessage]:
        """
        Keeps only the latest conversation messages.
        """

        limit = limit or cls.DEFAULT_LIMIT

        if len(history) <= limit:
            return history

        return history[-limit:]

    # =====================================================
    # Build Complete Conversation
    # =====================================================

    @classmethod
    def build_messages(
        cls,
        *,
        system_prompt: str,
        history: list[ChatMessage],
        user_message: str,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Returns the final payload for OpenAI.

        [
            system,
            history...,
            current user message
        ]
        """

        history = cls.trim(
            history=history,
            limit=limit,
        )

        conversation = cls.build(
            history=history,
        )

        return [
            {
                "role": "system",
                "content": system_prompt,
            },
            *conversation,
            {
                "role": "user",
                "content": user_message.strip(),
            },
        ]