"""
============================================================
Chat Repository

Handles:

- chat_sessions
- chat_messages
- tool_calls

No business logic.
============================================================
"""

from datetime import UTC, datetime
from typing import Any

from backend.app.core.enum.enums import ChatRole
from app.repositories.base import BaseRepository


class ChatRepository(BaseRepository):

    SESSION_TABLE = "chat_sessions"
    MESSAGE_TABLE = "chat_messages"
    TOOL_TABLE = "tool_calls"

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
        values: dict[str, Any],
    ) -> dict:

        result = (
            self.sessions()
            .insert(values)
            .execute()
        )

        return result.data[0]

    async def get_session(
        self,
        session_id: str,
    ) -> dict | None:

        result = (
            self.sessions()
            .select("*")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        Uses idx_sessions_user.
        """

        result = (
            self.sessions()
            .select("*")
            .eq("user_id", user_id)
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []

    async def list_org_sessions(
        self,
        org_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        Uses idx_sessions_org.
        """

        result = (
            self.sessions()
            .select("*")
            .eq("org_id", org_id)
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []

    async def update_session(
        self,
        session_id: str,
        values: dict[str, Any],
    ) -> dict:

        values["updated_at"] = datetime.now(UTC)

        result = (
            self.sessions()
            .update(values)
            .eq("id", session_id)
            .execute()
        )

        return result.data[0]

    async def archive_session(
        self,
        session_id: str,
    ) -> dict:
        """
        Mark a session as inactive.
        """

        return await self.update_session(
            session_id,
            {
                "is_active": False,
            },
        )
    
        # =========================================================
    # Messages
    # =========================================================

    async def create_message(
        self,
        values: dict[str, Any],
    ) -> dict:
        """
        Store a chat message.
        """

        result = (
            self.messages()
            .insert(values)
            .execute()
        )

        return result.data[0]

    async def get_message(
        self,
        message_id: str,
    ) -> dict | None:
        """
        Get a message by ID.
        """

        result = (
            self.messages()
            .select("*")
            .eq("id", message_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_session_messages(
        self,
        session_id: str,
    ) -> list[dict]:
        """
        Returns the complete conversation.

        Uses idx_messages_session.
        """

        result = (
            self.messages()
            .select("*")
            .eq("session_id", session_id)
            .order(
                "created_at",
                desc=False,
            )
            .execute()
        )

        return result.data or []

    async def list_recent_messages(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[dict]:
        """
        Returns the latest conversation history.

        Used for LLM context windows.
        """

        result = (
            self.messages()
            .select("*")
            .eq("session_id", session_id)
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        messages = result.data or []

        # Return oldest → newest for prompt construction
        return list(reversed(messages))

    async def list_org_messages(
        self,
        org_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        Uses idx_messages_org.
        """

        result = (
            self.messages()
            .select("*")
            .eq("org_id", org_id)
            .order(
                "created_at",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return result.data or []
    
        # =========================================================
    # Tool Calls
    # =========================================================

    async def create_tool_call(
        self,
        values: dict[str, Any],
    ) -> dict:
        """
        Store an AI tool call.
        """

        result = (
            self.tools()
            .insert(values)
            .execute()
        )

        return result.data[0]

    async def get_tool_call(
        self,
        tool_call_id: str,
    ) -> dict | None:
        """
        Get a tool call by ID.
        """

        result = (
            self.tools()
            .select("*")
            .eq("id", tool_call_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    async def list_message_tool_calls(
        self,
        message_id: str,
    ) -> list[dict]:
        """
        Return tool calls for a message.

        Uses idx_tool_calls_message.
        """

        result = (
            self.tools()
            .select("*")
            .eq("message_id", message_id)
            .execute()
        )

        return result.data or []

    async def list_session_tool_calls(
        self,
        session_id: str,
    ) -> list[dict]:
        """
        Return tool calls for a chat session.

        Uses idx_tool_calls_session.
        """

        result = (
            self.tools()
            .select("*")
            .eq("session_id", session_id)
            .order(
                "created_at",
                desc=False,
            )
            .execute()
        )

        return result.data or []

    async def list_tool_usage(
        self,
        org_id: str,
        tool_name: str,
    ) -> list[dict]:
        """
        Return usage for a specific tool.

        Uses idx_tool_calls_name.
        """

        result = (
            self.tools()
            .select("*")
            .eq("org_id", org_id)
            .eq("tool_name", tool_name)
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return result.data or []
    
        # =========================================================
    # Session State
    # =========================================================

    async def increment_session_statistics(
        self,
        session_id: str,
        messages: int,
        tokens: int,
        cost_usd: float,
    ) -> dict:
        """
        Update running chat statistics.

        The service supplies the new totals.
        """

        session = await self.get_session(session_id)

        if session is None:
            raise self.not_found("Chat session")

        values = {
            "total_messages": session["total_messages"] + messages,
            "total_tokens": session["total_tokens"] + tokens,
            "total_cost_usd": session["total_cost_usd"] + cost_usd,
            "updated_at": datetime.now(UTC),
        }

        result = (
            self.sessions()
            .update(values)
            .eq("id", session_id)
            .execute()
        )

        return result.data[0]

    async def attach_documents_to_session(
        self,
        session_id: str,
        document_ids: list[str],
    ) -> dict:
        """
        Replace session document context.
        """

        result = (
            self.sessions()
            .update(
                {
                    "document_ids": document_ids,
                    "updated_at": datetime.now(UTC),
                }
            )
            .eq("id", session_id)
            .execute()
        )

        return result.data[0]

    async def attach_vendors_to_session(
        self,
        session_id: str,
        vendor_ids: list[str],
    ) -> dict:
        """
        Replace session vendor context.
        """

        result = (
            self.sessions()
            .update(
                {
                    "vendor_ids": vendor_ids,
                    "updated_at": datetime.now(UTC),
                }
            )
            .eq("id", session_id)
            .execute()
        )

        return result.data[0]
    
        # =========================================================
    # Helpers
    # =========================================================

    async def session_exists(
        self,
        session_id: str,
    ) -> bool:

        result = (
            self.sessions()
            .select("id")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def message_exists(
        self,
        message_id: str,
    ) -> bool:

        result = (
            self.messages()
            .select("id")
            .eq("id", message_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    async def tool_call_exists(
        self,
        tool_call_id: str,
    ) -> bool:

        result = (
            self.tools()
            .select("id")
            .eq("id", tool_call_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)