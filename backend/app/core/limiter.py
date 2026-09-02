from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Redis-backed storage makes rate limits consistent across workers/instances.
# Failures in Redis should not be treated as application data failures.
def rate_limit_key(request):
    """Partition limits by client IP and selected workspace."""
    # The workspace header is never an authorization mechanism; OCM still
    # verifies membership. Including it here prevents one busy workspace
    # from consuming the whole IP bucket for unrelated workspaces.
    org_id = request.headers.get("X-Org-Id", "-")
    return f"ip:{get_remote_address(request)}:org:{org_id}"


limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=["200/minute"],
    storage_uri=settings.redis_url,
    headers_enabled=True,
)
