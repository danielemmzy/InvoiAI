"""
============================================================
Tool Handler

Executes OpenAI tool calls.

Responsibilities
----------------
- Parse tool arguments
- Execute ToolExecutor
- Return OpenAI tool messages

No repositories.
No OpenAI API calls.
============================================================
"""

from __future__ import annotations

import json
from typing import Any

from app.services.ai.tool_executor_service import ToolExecutor


class ToolHandler:

    def __init__(self):

        self.executor = ToolExecutor()

    async def handle(
        self,
        tool_call,
    ) -> dict[str, Any]:
        """
        Execute a single OpenAI tool call.
        """

        function = tool_call.function

        tool_name = function.name

        arguments = json.loads(
            function.arguments or "{}",
        )

        result = await self.executor.execute(
            tool_name=tool_name,
            arguments=arguments,
        )

        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(
                result,
                default=str,
            ),
        }

    async def handle_many(
        self,
        tool_calls,
    ) -> list[dict[str, Any]]:
        """
        Execute multiple tool calls.
        """

        results = []

        for tool_call in tool_calls:

            results.append(
                await self.handle(
                    tool_call,
                )
            )

        return results