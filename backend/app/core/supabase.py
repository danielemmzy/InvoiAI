from supabase import create_client, Client
from functools import lru_cache
from app.core.config import settings


@lru_cache
def get_supabase() -> Client:
    """
    Server-side Supabase client using the SERVICE ROLE key.

    Two types of Supabase keys:
      anon key        — for frontend/client use, respects RLS policies
      service role    — for backend use, bypasses RLS, full access

    We use service role here because:
      - Our FastAPI backend is trusted server-side code
      - We enforce our own auth checks in the routers
      - RLS on the DB is still active for direct client access
      - The service role key NEVER goes to the frontend

    IMPORTANT: Never expose SUPABASE_SERVICE_KEY in frontend code.
    """
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key   # service role, not anon key
    )