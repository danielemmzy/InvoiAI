"""
============================================================
app/core/supabase.py

Supabase Client Manager

This module is the ONLY place that creates Supabase clients.

Client Types

1. Service Client
   - Uses SERVICE_ROLE key
   - Bypasses RLS
   - Used by backend services

2. Public Client
   - Uses ANON key
   - Respects RLS
   - Used only when explicitly required

Never instantiate Supabase anywhere else.

============================================================
"""

from __future__ import annotations

import logging

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

_service_client: Client | None = None
_public_client: Client | None = None


# ============================================================
# Service Client
# ============================================================

def get_supabase() -> Client:
    """
    Returns the singleton service-role client.

    This client bypasses Row Level Security.

    Use for:
        - Background jobs
        - Backend services
        - Webhooks
        - AI pipelines
        - Organization Context Middleware
    """

    global _service_client

    if _service_client is None:
        _service_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )

        logger.info("Supabase service client initialized.")

    return _service_client


# ============================================================
# Public Client
# ============================================================

def get_public_supabase() -> Client:
    """
    Returns the singleton public client.

    Uses the anonymous key.

    Normally not needed because authentication
    is performed with JWTs.

    Available for future frontend/server
    interactions if required.
    """

    global _public_client

    if _public_client is None:
        _public_client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )

        logger.info("Supabase public client initialized.")

    return _public_client


# ============================================================
# Health Check
# ============================================================

def check_supabase_connection() -> bool:
    """
    Performs a lightweight connectivity check.

    Returns:
        True if Supabase is reachable.
    """

    try:
        get_supabase().table("profiles").select("id").limit(1).execute()
        return True

    except Exception as exc:
        logger.exception("Supabase health check failed: %s", exc)
        return False