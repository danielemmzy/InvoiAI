from supabase import create_client, Client
from functools import lru_cache
from app.core.config import settings
 
 
@lru_cache
def get_supabase() -> Client:
    # Returns a cached Supabase client instance for database interactions.
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key
    )