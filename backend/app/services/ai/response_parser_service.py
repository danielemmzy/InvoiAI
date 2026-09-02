"""
============================================================
Response Parser

Parses OpenAI responses into a consistent structure.

Responsibilities
----------------
- Extract assistant text
- Extract tool calls
- Extract usage
- Extract finish reason

No OpenAI requests.

No repositories.

No business logic.
============================================================
"""

from __future__ import annotations

import json
from typing import Any


class ResponseParser:
    """
    Parses OpenAI ChatCompletion responses.
    """

    # =====================================================
    # Message
    # =====================================================

    @staticmethod
    def message(response) -> Any:
        return response.choices[0].message

    # =====================================================
    # Assistant Text
    # =====================================================

    @classmethod
    def content(
        cls,
        response,
    ) -> str:

        message = cls.message(response)

        return (message.content or "").strip()

    # =====================================================
    # Tool Calls
    # =====================================================

    @classmethod
    def tool_calls(
        cls,
        response,
    ) -> list[dict]:

        message = cls.message(response)

        calls = message.tool_calls or []

        parsed: list[dict] = []

        for call in calls:

            arguments = call.function.arguments or "{}"

            parsed.append(
                {
                    "id": call.id,
                    "name": call.function.name,
                    "arguments": json.loads(arguments),
                }
            )

        return parsed

    # =====================================================
    # Usage
    # =====================================================

    @staticmethod
    def usage(
        response,
    ) -> dict:

        usage = response.usage

        if usage is None:

            return {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

        return {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

    # =====================================================
    # Finish Reason
    # =====================================================

    @staticmethod
    def finish_reason(
        response,
    ) -> str:

        return response.choices[0].finish_reason

    # =====================================================
    # Tool Request
    # =====================================================

    @classmethod
    def requires_tool(
        cls,
        response,
    ) -> bool:

        return (
            cls.finish_reason(response) == "tool_calls"
            or len(cls.tool_calls(response)) > 0
        )

    # =====================================================
    # Complete Parse
    # =====================================================

    @classmethod
    def parse(
        cls,
        response,
    ) -> dict:

        return {
            "content": cls.content(response),
            "tool_calls": cls.tool_calls(response),
            "usage": cls.usage(response),
            "finish_reason": cls.finish_reason(response),
            "requires_tool": cls.requires_tool(response),
        }