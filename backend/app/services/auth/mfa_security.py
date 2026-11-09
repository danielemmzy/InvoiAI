from __future__ import annotations

import hashlib
import secrets
import time


RECOVERY_CODE_COUNT = 10
STEP_UP_MAX_AGE_SECONDS = 300


def hash_recovery_code(code: str) -> str:
    normalized = code.strip().replace("-", "").upper()
    return hashlib.sha256(normalized.encode("ascii")).hexdigest()


def generate_recovery_codes() -> tuple[list[str], list[str]]:
    codes = [
        "-".join(secrets.token_hex(16).upper()[index:index + 4] for index in range(0, 32, 4))
        for _ in range(RECOVERY_CODE_COUNT)
    ]
    return codes, [hash_recovery_code(code) for code in codes]


def is_recent_aal2(
    assurance_level: str,
    mfa_verified_at: int | None,
    *,
    now: int | None = None,
) -> bool:
    current_time = int(time.time()) if now is None else now
    return (
        assurance_level == "aal2"
        and isinstance(mfa_verified_at, int)
        and not isinstance(mfa_verified_at, bool)
        and mfa_verified_at <= current_time + 30
        and current_time - mfa_verified_at <= STEP_UP_MAX_AGE_SECONDS
    )


def totp_verified_at(auth_methods: object) -> int | None:
    if not isinstance(auth_methods, list):
        return None
    timestamps = [
        method.get("timestamp")
        for method in auth_methods
        if isinstance(method, dict)
        and method.get("method") == "totp"
        and isinstance(method.get("timestamp"), int)
        and not isinstance(method.get("timestamp"), bool)
    ]
    return max(timestamps) if timestamps else None
