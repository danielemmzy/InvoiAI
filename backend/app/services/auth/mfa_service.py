from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.core.supabase import get_supabase, get_user_supabase
from app.services.auth.mfa_security import hash_recovery_code


def factors_for_user(access_token: str):
    return get_user_supabase(access_token).auth.mfa.list_factors()


def has_admin_membership(user_id: UUID | str) -> bool:
    rows = (
        get_supabase()
        .table("org_members")
        .select("id")
        .eq("user_id", str(user_id))
        .eq("is_active", True)
        .in_("role", ["owner", "admin"])
        .limit(1)
        .execute()
        .data
        or []
    )
    return bool(rows)


def replace_recovery_codes(user_id: UUID | str, hashes: list[str]) -> None:
    get_supabase().rpc(
        "replace_auth_mfa_recovery_codes",
        {"p_user_id": str(user_id), "p_code_hashes": hashes},
    ).execute()


def consume_recovery_code(
    user_id: UUID | str,
    session_id: str,
    code: str,
) -> bool:
    result = get_supabase().rpc(
        "consume_auth_mfa_recovery_code",
        {
            "p_user_id": str(user_id),
            "p_session_id": session_id,
            "p_code_hash": hash_recovery_code(code),
        },
    ).execute()
    return result.data is True


def has_recovery_step_up(user_id: UUID | str, session_id: str | None) -> bool:
    if not session_id:
        return False
    now = datetime.now(timezone.utc).isoformat()
    rows = (
        get_supabase()
        .table("auth_mfa_recovery_step_ups")
        .select("session_id")
        .eq("user_id", str(user_id))
        .eq("session_id", session_id)
        .gt("expires_at", now)
        .limit(1)
        .execute()
        .data
        or []
    )
    return bool(rows)
