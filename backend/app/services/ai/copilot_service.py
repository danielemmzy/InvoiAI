from __future__ import annotations

from decimal import Decimal
import time
from uuid import UUID

from openai import AsyncOpenAI

from app.core.config import settings

from app.repositories.ai.chat_repository import ChatRepository

from app.services.ai.conversation_builder import (
    ConversationBuilder,
)

from app.services.ai.cost_calculator import (
    CostCalculator,
)

from app.services.ai.prompt_builder import (
    PromptBuilder,
)

from app.services.ai.response_parser_service import (
    ResponseParser,
)

from app.services.ai.tool_definitions import (
    TOOLS,
    get_tools_for_mode,
)

from app.services.ai.tool_executor_service import (
    ToolExecutor,
)

from app.services.search_service import SearchService

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
)



class CopilotService:
    """
    AI Copilot orchestration layer.

    Responsibilities
    ----------------
    - Conversation management
    - Semantic retrieval
    - Prompt construction
    - LLM generation
    - Tool execution
    - Usage tracking
    - Session updates
    """

    MODEL = "gpt-4.1-mini"

    def __init__(
        self,
        *,
        chat_repository: ChatRepository | None = None,
        search_service: SearchService | None = None,
        tool_executor: ToolExecutor | None = None,
    ):
        self.chat_repository = chat_repository or ChatRepository()
        self.search = search_service or SearchService()
        self.tool_executor = tool_executor or ToolExecutor(search_service=self.search)

        self.prompt_builder = PromptBuilder()

        self.conversation_builder = ConversationBuilder()

        self.response_parser = ResponseParser()

        self.cost_calculator = CostCalculator()

    # =========================================================
    # Public API
    # =========================================================

    async def send_message(
    self,
    *,
    session_id: UUID,
    org_id: UUID,
    user_id: UUID,
    message: str,
    personal_mode: bool = False,
):

        started = time.perf_counter()

        session = await self._load_session(
            session_id,
        )

        # Personal and business copilots intentionally have different context
        # boundaries. Personal mode must never retrieve business document/vendor
        # memory simply because both workspaces share the same authenticated user.
        if personal_mode:
            retrieval = {
                "context": "",
                "documents": [],
                "vendors": [],
                "organization": [],
                "statistics": {},
            }
        else:
            retrieval = await self.search.retrieve(
                org_id=org_id,
                query=message,
            )

        history = await self.chat_repository.list_recent_messages(
            session_id=session_id,
            limit=20,
        )

        messages = self._build_messages(
            context=retrieval["context"],
            history=history,
            message=message,
        )

        response = await self._call_model(
            messages,
            tools=get_tools_for_mode(personal_mode),
        )

        tool_messages = await self._execute_tool_calls(
            response,
            org_id=org_id,
            user_id=user_id,
        )

        if tool_messages:

            messages.append(
                response.choices[0]
                .message
                .model_dump(
                    exclude_none=True,
                )
            )

            messages.extend(
                tool_messages,
            )

            response = await self._call_model(
                messages,
                tools=get_tools_for_mode(personal_mode),
            )

        assistant_message = (
            self.response_parser.parse_assistant_message(
                response,
            )
        )

        usage = self.response_parser.extract_usage(
            response,
        )

        total_tokens = (
            usage.total_tokens
            if usage
            else 0
        )

        latency_ms = int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

        cost = self.cost_calculator.calculate(
            model=self.MODEL,
            usage=usage,
        )

        await self._save_user_message(
            session_id=session_id,
            org_id=org_id,
            user_id=user_id,
            message=message,
            retrieval=retrieval,
        )

        assistant_record = await self._save_assistant_message(
            session_id=session_id,
            org_id=org_id,
            user_id=user_id,
            content=assistant_message,
            retrieval=retrieval,
            tokens=total_tokens,
            latency_ms=latency_ms,
            cost=cost,
        )

        await self._update_session(
            session=session,
            session_id=session_id,
            tokens=total_tokens,
            cost=cost,
        )

        return self._build_response(
            assistant_record=assistant_record,
            answer=assistant_message,
            retrieval=retrieval,
            latency_ms=latency_ms,
            tokens=total_tokens,
        )
    
    # =========================================================
    # Session
    # =========================================================

    def _build_messages(
        self,
        *,
        context: str,
        history,
        message: str,
    ) -> list[dict]:

        system_prompt, user_prompt = (
            self.prompt_builder.build(
                context=context,
                message=message,
            )
        )

        return self.conversation_builder.build_messages(
            system_prompt=system_prompt,
            history=history,
            user_message=user_prompt,
        )

    # =========================================================
    # OpenAI
    # =========================================================

    async def _call_model(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ):

        response = await client.chat.completions.create(
            model=self.MODEL,
            temperature=0.2,
            messages=messages,
            tools=tools or TOOLS,
            tool_choice="auto",
        )

        return response

    # =========================================================
    # Tool Calls
    # =========================================================

    async def _execute_tool_calls(
        self,
        response,
        *,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ):

        message = response.choices[0].message

        if not message.tool_calls:
            return None

        tool_outputs = []

        for tool_call in message.tool_calls:

            result = await self.tool_executor.execute(
                tool_name=tool_call.function.name,
                arguments=self.response_parser.parse_tool_arguments(
                    tool_call.function.arguments,
                ),
                org_id=org_id,
                user_id=user_id,
            )

            tool_outputs.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": self.response_parser.serialize_tool_result(
                        result,
                    ),
                }
            )

        return tool_outputs

    # =========================================================
    # Persistence
    # =========================================================

    async def _save_user_message(
        self,
        *,
        session_id: UUID,
        org_id: UUID,
        user_id: UUID,
        message: str,
        retrieval: dict,
    ):

        await self.chat_repository.create_message(
            {
                "session_id": session_id,
                "org_id": org_id,
                "user_id": user_id,
                "role": "user",
                "content": message,
                "context_used": retrieval,
                "retrieved_docs": retrieval.get(
                    "documents",
                    [],
                ),
                "retrieved_vendors": retrieval.get(
                    "vendors",
                    [],
                ),
                "tokens_used": 0,
                "model_used": self.MODEL,
                "latency_ms": 0,
                "cost_usd": Decimal("0"),
            }
        )

    async def _save_assistant_message(
        self,
        *,
        session_id: UUID,
        org_id: UUID,
        user_id: UUID,
        content: str,
        retrieval: dict,
        tokens: int,
        latency_ms: int,
        cost: Decimal,
    ):

        return await self.chat_repository.create_message(
            {
                "session_id": session_id,
                "org_id": org_id,
                "user_id": user_id,
                "role": "assistant",
                "content": content,
                "context_used": retrieval,
                "retrieved_docs": retrieval.get(
                    "documents",
                    [],
                ),
                "retrieved_vendors": retrieval.get(
                    "vendors",
                    [],
                ),
                "tokens_used": tokens,
                "model_used": self.MODEL,
                "latency_ms": latency_ms,
                "cost_usd": cost,
            }
        )

    async def _update_session(
        self,
        *,
        session,
        session_id: UUID,
        tokens: int,
        cost: Decimal,
    ):

        await self.chat_repository.update_session(
            session_id,
            {
                "total_messages":
                    session.total_messages + 2,
                "total_tokens":
                    session.total_tokens + tokens,
                "total_cost_usd":
                    session.total_cost_usd + cost,
            },
        )

    # =========================================================
    # Helpers
    # =========================================================


    @staticmethod
    def _build_response(
        *,
        assistant_record,
        answer: str,
        retrieval: dict,
        latency_ms: int,
        tokens: int,
    ) -> dict:

        return {
            "message": assistant_record,
            "answer": answer,
            "documents": retrieval.get(
                "documents",
                [],
            ),
            "vendors": retrieval.get(
                "vendors",
                [],
            ),
            "organization": retrieval.get(
                "organization",
                [],
            ),
            "statistics": retrieval.get(
                "statistics",
                {},
            ),
            "latency_ms": latency_ms,
            "tokens": tokens,
        }