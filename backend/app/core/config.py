"""
============================================================
app/core/config.py

Application configuration.

This file is the SINGLE source of truth for runtime
configuration loaded from environment variables.

Rules:

• Environment variables ONLY
• No business logic
• No plan limits
• No feature flags
• No AI weights
• No permissions

Everything else belongs in its own module.

Loaded once and cached for the lifetime of the application.
============================================================
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Runtime application configuration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================================================
    # Application
    # ========================================================

    app_name: str = "InvoiAI"
    app_version: str = "2.2.0"
    frontend_app_url: str = "http://localhost:3000"

    environment: str = "development"
    debug: bool = False

    secret_key: str

    # ========================================================
    # API
    # ========================================================

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
        ]
    )

    # ========================================================
    # Database (Supabase)
    # ========================================================

    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # ========================================================
    # OpenAI / AI Providers (GL coding, extraction, classification)
    # ========================================================

    openai_api_key: str = ""

    # GL coding AI is optional. Rules, vendor history and manual assignments
    # work without it, so keep it off until a working provider/key is configured.
    ap_gl_ai_enabled: bool = False

    # AI provider selection: "openai" | "gemini" | "groq" | "local" | "disabled"
    # Keep AI disabled by default until a working provider is configured.
    ai_provider: str = "disabled"
    ai_model: str = ""
    ai_base_url: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    local_api_key: str = ""

    # ========================================================
    # Stripe
    # ========================================================

    stripe_secret_key: str
    stripe_webhook_secret: str

    stripe_price_free: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_business: str = ""
    stripe_price_starter_annual: str = ""
    stripe_price_pro_annual: str = ""
    stripe_price_business_annual: str = ""
    stripe_price_enterprise: str = ""

    # ========================================================
    # Google OAuth
    # ========================================================

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = (
        "http://localhost:8000/api/v2/integrations/google/callback"
    )

    # ========================================================
    # QuickBooks OAuth
    # ========================================================

    quickbooks_client_id: str = ""
    quickbooks_client_secret: str = ""
    quickbooks_redirect_uri: str = (
        "http://localhost:8000/api/v2/integrations/quickbooks/callback"
    )

    quickbooks_environment: str = "sandbox"

    # ========================================================
    # Xero OAuth
    # ========================================================

    xero_client_id: str = ""
    xero_client_secret: str = ""
    xero_redirect_uri: str = (
        "http://localhost:8000/api/v2/integrations/xero/callback"
    )

    # ========================================================
    # Redis
    # ========================================================

    redis_url: str = "redis://localhost:6379/0"

    redis_max_connections: int = 100

    # Blocking Supabase/PostgREST calls run in a bounded worker pool so they
    # never stall the asyncio event loop. Sized to overlap network latency, not
    # to create unbounded threads.
    db_thread_pool_size: int = 32

    # Distributed scheduler locking. Required in production so multiple
    # application workers cannot execute the same cron job concurrently.
    scheduler_lock_enabled: bool = True
    scheduler_lock_ttl_seconds: int = 300
    # Fail closed in production when Redis is unavailable. Development may
    # opt into fail-open behaviour for local work without Redis.
    scheduler_lock_fail_open: bool = True

    # ========================================================
    # Background Workers
    # ========================================================

    queue_name_default: str = "default"
    queue_name_ai: str = "ai"
    queue_name_sync: str = "sync"
    queue_name_email: str = "email"

    worker_concurrency: int = 4

    # ========================================================
    # Accounts Payable recovery
    # ========================================================
    # A document in validating/matching/coding older than this is considered
    # abandoned and may be resumed by the cron sweeper.
    ap_recovery_lease_seconds: int = 900
    ap_recovery_max_attempts: int = 5
    ap_recovery_sweep_limit: int = 25

    # ========================================================
    # Email
    # ========================================================
    ap_email_webhook_secret: str = ""
    ap_email_inbound_domain: str = "inbound.invoiai.com"

    smtp_host: str = ""
    smtp_port: int = 587

    smtp_username: str = ""
    smtp_password: str = ""

    smtp_sender_name: str = "InvoiAI"
    smtp_sender_email: str = ""

    # ========================================================
    # Storage
    # ========================================================

    storage_bucket: str = "documents"

    # Accepted document MIME types for the V2 intake endpoint.
    allowed_file_types: set[str] = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    max_file_size_mb: int = 10

    # ========================================================
    # Logging
    # ========================================================

    log_level: str = "INFO"

    # ========================================================
    # Security
    # ========================================================

    access_token_expire_minutes: int = 60

    refresh_token_expire_days: int = 30

    password_reset_expire_minutes: int = 30

    # AES-256-GCM key for OAuth tokens. Base64url-encoded 32 bytes.
    token_encryption_key: str = ""

    # Six-digit email verification OTP. Codes are hashed with
    # OTP_HASH_SECRET; when unset, SECRET_KEY is used as the pepper.
    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_max_resends_per_hour: int = 5
    otp_hash_secret: str = ""

    # ========================================================
    # Feature Toggles
    # ========================================================

    enable_docs: bool = True
    enable_openapi: bool = True

    # ========================================================
    # Monitoring
    # ========================================================

    sentry_dsn: str = ""

    # Optional incident-alert webhook. Empty means alerts are logged only.
    alert_webhook_url: str = ""

    # Named owner for alerts; surfaced in the operator runbook.
    alert_owner: str = "Platform on-call"

    # ========================================================
    # Google Service Account
    # ========================================================

    google_project_id: str = ""

    google_private_key_id: str = ""

    google_private_key: str = ""

    google_service_account_email: str = ""

    # ========================================================
    # Google Document AI
    # ========================================================

    google_location: str = ""

    google_processor_id: str = ""


@lru_cache
def get_settings() -> Settings:
    """
    Returns the cached application settings.

    This ensures environment variables are parsed only once
    during application startup.
    """
    return Settings()


settings = get_settings()