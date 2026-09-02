"""
============================================================
Chat Mapper
============================================================
"""

from app.mappers.base import BaseMapper

from app.models.domain.chat import (
    ChatMessage,
    ChatSession,
    ToolCall,
)

from app.schemas.chat import (
    ChatMessageResponse,
    ChatSessionResponse,
    ToolCallResponse,
)


class ChatSessionMapper(
    BaseMapper[
        ChatSession,
        ChatSessionResponse,
    ]
):
    domain_model = ChatSession
    response_model = ChatSessionResponse


class ChatMessageMapper(
    BaseMapper[
        ChatMessage,
        ChatMessageResponse,
    ]
):
    domain_model = ChatMessage
    response_model = ChatMessageResponse

class ToolCallMapper(
    BaseMapper[
        ToolCall,
        ToolCallResponse,
    ]
):
    domain_model = ToolCall
    response_model = ToolCallResponse