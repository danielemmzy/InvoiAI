from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.core.enum.application import ApprovalStatus
from app.core.enum.database import ApprovalDecision

from app.mappers.chat_mapper import (
    ChatMessageMapper,
    ChatSessionMapper,
    ToolCallMapper,
)

from app.models.domain.chat import (
    ChatMessage,
    ChatSession,
    ToolCall,
)

from app.repositories.base import BaseRepository


class ChatRepository(BaseRepository):
    """
    Repository for chat persistence.

    Owns three tables:

    - chat_sessions
    - chat_messages
    - tool_calls
    """

    table_name = "chat_sessions"
    mapper = ChatSessionMapper

    SESSION_TABLE = "chat_sessions"
    MESSAGE_TABLE = "chat_messages"
    TOOL_TABLE = "tool_calls"

    # =========================================================
    # Table Helpers
    # =========================================================

    def sessions(self):
        return self.db.table(self.SESSION_TABLE)

    def messages(self):
        return self.db.table(self.MESSAGE_TABLE)

    def tools(self):
        return self.db.table(self.TOOL_TABLE)

    # =========================================================
    # Sessions
    # =========================================================

    async def create_session(
        self,
        session: ChatSession | dict,
    ) -> ChatSession | None:
        return await self.create(session)

    async def get_session(
        self,
        session_id: UUID,
    ) -> ChatSession | None:
        return await self.get(session_id)

    async def update_session(
        self,
        session_id: UUID,
        values,
    ) -> ChatSession | None:

        if isinstance(values, dict):
            values["updated_at"] = datetime.now(UTC)

        return await self.update(
            session_id,
            values,
        )

    async def list_user_sessions(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[ChatSession]:

        response = (
            self.sessions()
            .select("*")
            .eq("user_id", str(user_id))
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        old = self.mapper
        self.mapper = ChatSessionMapper
        result = self._many(response)
        self.mapper = old

        return result

    async def list_org_sessions(
        self,
        org_id: UUID,
        limit: int = 100,
    ) -> list[ChatSession]:

        response = (
            self.sessions()
            .select("*")
            .eq("org_id", str(org_id))
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        old = self.mapper
        self.mapper = ChatSessionMapper
        result = self._many(response)
        self.mapper = old

        return result

    async def archive_session(
        self,
        session_id: UUID,
    ) -> ChatSession | None:

        return await self.update_session(
            session_id,
            {
                "is_active": False,
            },
        )

    async def session_exists(
        self,
        session_id: UUID,
    ) -> bool:

        old = self.table_name
        self.table_name = self.SESSION_TABLE

        exists = await self.exists(
            "id",
            session_id,
        )

        self.table_name = old

        return exists
    # =========================================================
    # Messages
    # =========================================================

    async def create_message(
        self,
        message: ChatMessage | dict,
    ) -> ChatMessage | None:

        response = (
            self.messages()
            .insert(
                ChatMessageMapper.to_insert(message)
            )
            .execute()
        )

        return ChatMessageMapper.to_domain(
            self.raw(response)
        )


    async def get_message(
        self,
        message_id: UUID,
    ) -> ChatMessage | None:

        response = (
            self.messages()
            .select("*")
            .eq("id", str(message_id))
            .limit(1)
            .execute()
        )

        row = self.raw(response)

        return (
            ChatMessageMapper.to_domain(row)
            if row
            else None
        )


    async def list_session_messages(
        self,
        session_id: UUID,
    ) -> list[ChatMessage]:

        response = (
            self.messages()
            .select("*")
            .eq("session_id", str(session_id))
            .order(
                "created_at",
                desc=False,
            )
            .execute()
        )

        return ChatMessageMapper.to_domain_list(
            self.raw_many(response)
        )


    async def list_recent_messages(
        self,
        session_id: UUID,
        limit: int = 20,
    ) -> list[ChatMessage]:

        response = (
            self.messages()
            .select("*")
            .eq("session_id", str(session_id))
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        messages = ChatMessageMapper.to_domain_list(
            self.raw_many(response)
        )

        return list(reversed(messages))


    async def list_org_messages(
        self,
        org_id: UUID,
        limit: int = 100,
    ) -> list[ChatMessage]:

        response = (
            self.messages()
            .select("*")
            .eq("org_id", str(org_id))
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return ChatMessageMapper.to_domain_list(
            self.raw_many(response)
        )


    async def message_exists(
        self,
        message_id: UUID,
    ) -> bool:

        response = (
            self.messages()
            .select("id")
            .eq("id", str(message_id))
            .limit(1)
            .execute()
        )

        return bool(response.data)
    
    # =========================================================
    # Tool Calls
    # =========================================================

    async def create_tool_call(
        self,
        tool_call: ToolCall | dict,
    ) -> ToolCall | None:

        response = (
            self.tools()
            .insert(
                ToolCallMapper.to_insert(tool_call)
            )
            .execute()
        )

        row = self.raw(response)

        return (
            ToolCallMapper.to_domain(row)
            if row
            else None
        )


    async def get_tool_call(
        self,
        tool_call_id: UUID,
    ) -> ToolCall | None:

        response = (
            self.tools()
            .select("*")
            .eq("id", str(tool_call_id))
            .limit(1)
            .execute()
        )

        row = self.raw(response)

        return (
            ToolCallMapper.to_domain(row)
            if row
            else None
        )


    async def list_message_tool_calls(
        self,
        message_id: UUID,
    ) -> list[ToolCall]:

        response = (
            self.tools()
            .select("*")
            .eq("message_id", str(message_id))
            .execute()
        )

        return ToolCallMapper.to_domain_list(
            self.raw_many(response)
        )


    async def list_session_tool_calls(
        self,
        session_id: UUID,
    ) -> list[ToolCall]:

        response = (
            self.tools()
            .select("*")
            .eq("session_id", str(session_id))
            .order(
                "created_at",
                desc=False,
            )
            .execute()
        )

        return ToolCallMapper.to_domain_list(
            self.raw_many(response)
        )


    async def list_tool_usage(
        self,
        org_id: UUID,
        tool_name: str,
    ) -> list[ToolCall]:

        response = (
            self.tools()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("tool_name", tool_name)
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return ToolCallMapper.to_domain_list(
            self.raw_many(response)
        )


    async def tool_call_exists(
        self,
        tool_call_id: UUID,
    ) -> bool:

        response = (
            self.tools()
            .select("id")
            .eq("id", str(tool_call_id))
            .limit(1)
            .execute()
        )

        return bool(response.data)