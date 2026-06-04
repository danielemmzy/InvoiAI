from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    # OpenAI
    openai_api_key: str

    # Supabase
    supabase_url: str
    supabase_anon_key: str      # frontend use only — never use in backend
    supabase_service_key: str   # backend only — bypasses RLS

    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str

    # App
    app_name: str = "InvoiAI"
    debug: bool = False
    max_file_size_mb: int = 10
    allowed_file_types: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    ]

    # Plan limits — invoices per month
    plan_limits: dict[str, int] = {
        "free": 10,
        "starter": 100,
        "pro": 500,
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()