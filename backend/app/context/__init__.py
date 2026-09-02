"""
============================================================
Application Context Objects

Request-scoped runtime context shared across
services, repositories, AI orchestration and MCP.

These objects are never persisted.

============================================================
"""

from .ai import AIContext
from .analysis import AnalysisContext
from .approval import ApprovalContext
from .audit import AuditContext
from .auth import AuthContext, AuthUser
from .chat import ChatContext
from .document import DocumentContext
from .execution import ExecutionContext
from .integration import IntegrationContext
from .job import JobContext
from .memory import MemoryContext
from .organization import OrganizationContext
from .request import RequestContext
from .tool import ToolContext
from .vendor import VendorContext

__all__ = [
    "AIContext",
    "AnalysisContext",
    "ApprovalContext",
    "AuditContext",
    "AuthContext",
    "AuthUser",
    "ChatContext",
    "DocumentContext",
    "ExecutionContext",
    "IntegrationContext",
    "JobContext",
    "MemoryContext",
    "OrganizationContext",
    "RequestContext",
    "ToolContext",
    "VendorContext",
]