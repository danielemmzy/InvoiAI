"""
============================================================
Health Service

Responsibilities
----------------
- Application health checks
- Dependency monitoring
- Readiness checks
- Liveness checks

No FastAPI.
No HTTP.

Used by:
    /health
    /ready
    /live
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime

from openai import AsyncOpenAI

from app.core.config import settings
from app.repositories.health_repository import HealthRepository


class HealthService:
    """
    Central application health checks.
    """

    def __init__(self):

        self.repository = HealthRepository()

        self.openai = AsyncOpenAI(
            api_key=settings.openai_api_key,
        )

    # =====================================================
    # Public
    # =====================================================

    async def health(self) -> dict:

        database = await self.database()

        redis = await self.redis()

        storage = await self.storage()

        smtp = await self.smtp()

        openai = await self.openai_status()

        healthy = all(
            [
                database["healthy"],
                redis["healthy"],
                storage["healthy"],
                smtp["healthy"],
                openai["healthy"],
            ]
        )

        return {
            "status": (
                "healthy"
                if healthy
                else "unhealthy"
            ),
            "timestamp": datetime.now(
                UTC
            ).isoformat(),
            "checks": {
                "database": database,
                "redis": redis,
                "storage": storage,
                "smtp": smtp,
                "openai": openai,
            },
        }

    async def readiness(self) -> dict:

        database = await self.database()

        ready = database["healthy"]

        return {
            "ready": ready,
            "database": database,
        }

    async def liveness(self) -> dict:

        return {
            "alive": True,
            "timestamp": datetime.now(
                UTC
            ).isoformat(),
        }

    # =====================================================
    # Database
    # =====================================================

    async def database(self) -> dict:

        try:

            await self.repository.ping()

            return {
                "healthy": True,
                "provider": "Supabase",
            }

        except Exception as exc:

            return {
                "healthy": False,
                "provider": "Supabase",
                "error": str(exc),
            }

    # =====================================================
    # OpenAI
    # =====================================================

    async def openai_status(self) -> dict:

        try:

            await self.openai.models.list()

            return {
                "healthy": True,
                "provider": "OpenAI",
            }

        except Exception as exc:

            return {
                "healthy": False,
                "provider": "OpenAI",
                "error": str(exc),
            }

    # =====================================================
    # Redis
    # =====================================================

    async def redis(self) -> dict:

        try:

            import redis.asyncio as redis

            client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

            await client.ping()

            await client.close()

            return {
                "healthy": True,
                "provider": "Redis",
            }

        except Exception as exc:

            return {
                "healthy": False,
                "provider": "Redis",
                "error": str(exc),
            }

    # =====================================================
    # SMTP
    # =====================================================

    async def smtp(self) -> dict:

        try:

            import smtplib

            server = smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=10,
            )

            server.ehlo()

            server.quit()

            return {
                "healthy": True,
                "provider": "SMTP",
            }

        except Exception as exc:

            return {
                "healthy": False,
                "provider": "SMTP",
                "error": str(exc),
            }

    # =====================================================
    # Storage
    # =====================================================

    async def storage(self) -> dict:

        try:

            (
                self.db.storage
                .from_(settings.storage_bucket)
                .list()
            )

            return {
                "healthy": True,
                "provider": "Supabase Storage",
            }

        except Exception as exc:

            return {
                "healthy": False,
                "provider": "Supabase Storage",
                "error": str(exc),
            }