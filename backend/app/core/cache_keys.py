"""Canonical Redis cache keys used by V2 application services.

Keep keys deterministic and scoped to the smallest safe owner boundary.
Never cache secrets, OAuth tokens, raw documents, or authorization headers.
"""

def industries() -> str:
    return "v2:industries:list"

def organization(org_id: str) -> str:
    return f"v2:organization:{org_id}:current"

def organization_permissions(org_id: str, user_id: str) -> str:
    return f"v2:organization:{org_id}:permissions:{user_id}"

def vendors(org_id: str, query: str | None, limit: int) -> str:
    normalized = (query or "").strip().lower()
    return f"v2:vendors:{org_id}:{limit}:{normalized}"

def insights(org_id: str, limit: int, offset: int) -> str:
    return f"v2:insights:{org_id}:{limit}:{offset}"
