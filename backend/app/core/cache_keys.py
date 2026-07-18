"""
============================================================
app/core/cache_keys.py

Centralized Redis cache key builders.

Never hardcode Redis keys anywhere in the application.

Benefits
--------
• Consistent cache naming
• Prevent key collisions
• Easier cache invalidation
• Easier monitoring
• Easier Redis migrations

Examples

org:8a7d...
vendor:91bc...
document:11aa...
usage:8a7d:2026-07
============================================================
"""

from typing import Final

# ============================================================
# Prefixes
# ============================================================

ORG_PREFIX: Final = "org"

USER_PREFIX: Final = "user"

MEMBER_PREFIX: Final = "member"

DOCUMENT_PREFIX: Final = "document"

VENDOR_PREFIX: Final = "vendor"

ANALYSIS_PREFIX: Final = "analysis"

USAGE_PREFIX: Final = "usage"

SETTINGS_PREFIX: Final = "settings"

INTEGRATION_PREFIX: Final = "integration"

PERMISSION_PREFIX: Final = "permission"

FEATURE_PREFIX: Final = "feature"

JOB_PREFIX: Final = "job"

RATE_LIMIT_PREFIX: Final = "rate_limit"

LOCK_PREFIX: Final = "lock"

SESSION_PREFIX: Final = "session"

WEBSOCKET_PREFIX: Final = "ws"

AI_PREFIX: Final = "ai"

EMBEDDING_PREFIX: Final = "embedding"


# ============================================================
# Organization
# ============================================================

def org(org_id: str) -> str:
    return f"{ORG_PREFIX}:{org_id}"


def organization_settings(org_id: str) -> str:
    return f"{SETTINGS_PREFIX}:{org_id}"


def organization_features(org_id: str) -> str:
    return f"{FEATURE_PREFIX}:{org_id}"


# ============================================================
# Members / Users
# ============================================================

def user(user_id: str) -> str:
    return f"{USER_PREFIX}:{user_id}"


def member(org_id: str, user_id: str) -> str:
    return f"{MEMBER_PREFIX}:{org_id}:{user_id}"


def permissions(org_id: str, user_id: str) -> str:
    return f"{PERMISSION_PREFIX}:{org_id}:{user_id}"


# ============================================================
# Documents
# ============================================================

def document(document_id: str) -> str:
    return f"{DOCUMENT_PREFIX}:{document_id}"


def document_analysis(document_id: str) -> str:
    return f"{ANALYSIS_PREFIX}:{document_id}"


def embedding(document_id: str) -> str:
    return f"{EMBEDDING_PREFIX}:{document_id}"


# ============================================================
# Vendors
# ============================================================

def vendor(vendor_id: str) -> str:
    return f"{VENDOR_PREFIX}:{vendor_id}"


def vendor_summary(org_id: str) -> str:
    return f"{VENDOR_PREFIX}:summary:{org_id}"


# ============================================================
# Usage
# ============================================================

def usage(org_id: str, month: str) -> str:
    return f"{USAGE_PREFIX}:{org_id}:{month}"


# ============================================================
# Integrations
# ============================================================

def integration(org_id: str, provider: str) -> str:
    return f"{INTEGRATION_PREFIX}:{org_id}:{provider}"


# ============================================================
# Background Jobs
# ============================================================

def job(job_id: str) -> str:
    return f"{JOB_PREFIX}:{job_id}"


def job_status(job_id: str) -> str:
    return f"{JOB_PREFIX}:status:{job_id}"


# ============================================================
# Rate Limiting
# ============================================================

def rate_limit(identifier: str) -> str:
    return f"{RATE_LIMIT_PREFIX}:{identifier}"


# ============================================================
# Distributed Locks
# ============================================================

def lock(name: str) -> str:
    return f"{LOCK_PREFIX}:{name}"


# ============================================================
# Sessions
# ============================================================

def session(session_id: str) -> str:
    return f"{SESSION_PREFIX}:{session_id}"


# ============================================================
# AI
# ============================================================

def ai_context(conversation_id: str) -> str:
    return f"{AI_PREFIX}:context:{conversation_id}"


def ai_response(response_id: str) -> str:
    return f"{AI_PREFIX}:response:{response_id}"


# ============================================================
# WebSockets
# ============================================================

def websocket(org_id: str) -> str:
    return f"{WEBSOCKET_PREFIX}:{org_id}"