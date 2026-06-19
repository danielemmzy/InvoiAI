from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    # OpenAI
    openai_api_key: str

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str

    # Stripe Price IDs — create these in your Stripe dashboard
    # Products → Add product → Add price → copy the price ID
    stripe_price_starter: str = ""   
    stripe_price_pro: str = ""        

    # Google Sheets — from service account JSON file
    google_project_id: str = ""
    google_private_key_id: str = ""
    google_private_key: str = ""      # paste full key with \n between lines
    google_service_account_email: str = ""

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
    # Matches plan_type enum in schema.sql
    plan_limits: dict[str, int] = {
        "free": 5,
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