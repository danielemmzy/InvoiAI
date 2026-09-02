from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt

from app.core.config import settings
from app.core.enum.database import IntegrationProvider
from app.integrations.quickbooks.oauth import QuickBooksOAuth
from app.integrations.xero.oauth import XeroOAuth
from app.models.domain.integration import IntegrationConnection
from app.repositories.integration.integration_repository import IntegrationConnectionRepository
from app.services.token_service import TokenService


class IntegrationService:
    """Application service for provider OAuth and connection lifecycle.

    OAuth providers own transport details. The service owns state validation,
    connection persistence, and organization-scoped lifecycle rules.
    """

    STATE_TTL_SECONDS = 600

    def __init__(
        self,
        *,
        repository: IntegrationConnectionRepository,
        quickbooks_oauth: QuickBooksOAuth,
        xero_oauth: XeroOAuth,
        token_service: TokenService,
    ) -> None:
        self.repository = repository
        self.quickbooks_oauth = quickbooks_oauth
        self.xero_oauth = xero_oauth
        self.tokens = token_service

    def build_authorization_url(
        self,
        *,
        provider: IntegrationProvider,
        user_id: UUID,
        org_id: UUID,
    ) -> str:
        state = self._build_state(
            provider=provider,
            user_id=user_id,
            org_id=org_id,
        )

        if provider is IntegrationProvider.QUICKBOOKS:
            return self.quickbooks_oauth.authorization_url(state=state)
        if provider is IntegrationProvider.XERO:
            return self.xero_oauth.authorization_url(state=state)
        raise ValueError(f"Unsupported integration provider: {provider.value}")

    async def complete_oauth(
        self,
        *,
        provider: IntegrationProvider,
        code: str,
        state: str,
        realm_id: str | None = None,
    ) -> IntegrationConnection:
        claims = self._verify_state(state)
        if claims["provider"] != provider.value:
            raise ValueError("OAuth state provider mismatch")

        org_id = UUID(claims["org_id"])
        user_id = UUID(claims["user_id"])

        if provider is IntegrationProvider.QUICKBOOKS:
            tokens = await self.quickbooks_oauth.exchange_code(code=code)
            resolved_realm_id = realm_id or tokens.get("realmId")
            if not resolved_realm_id:
                raise ValueError("QuickBooks did not return a realm id")

            values = self._connection_values(
                provider=provider,
                org_id=org_id,
                user_id=user_id,
                tokens=tokens,
                realm_id=resolved_realm_id,
            )
        elif provider is IntegrationProvider.XERO:
            tokens = await self.xero_oauth.exchange_code(code=code)
            values = self._connection_values(
                provider=provider,
                org_id=org_id,
                user_id=user_id,
                tokens=tokens,
                tenant_id=tokens.get("tenant_id"),
                account_name=tokens.get("tenant_name"),
            )
        else:
            raise ValueError(f"Unsupported integration provider: {provider.value}")

        encrypted = self.tokens.encrypt_token_fields(
            access_token=values["access_token"],
            refresh_token=values.get("refresh_token"),
        )
        values["access_token"] = encrypted["access_token"]
        values["refresh_token"] = encrypted["refresh_token"]

        existing = await self.repository.get_org_connection(org_id, provider)
        if existing:
            return await self.repository.update_connection(existing.id, values)

        return await self.repository.create_connection(
            IntegrationConnection(
                id=uuid4(),
                **values,
            )
        )

    async def list_connections(self, *, org_id: UUID) -> list[IntegrationConnection]:
        return await self.repository.list_org_connections(org_id)

    async def disconnect(
        self,
        *,
        connection: IntegrationConnection,
    ) -> None:
        hydrated = self.tokens.decrypt_connection(connection)
        if hydrated.refresh_token:
            if connection.provider is IntegrationProvider.QUICKBOOKS:
                await self.quickbooks_oauth.revoke(
                    refresh_token=hydrated.refresh_token,
                )
            elif connection.provider is IntegrationProvider.XERO:
                await self.xero_oauth.revoke(
                    refresh_token=hydrated.refresh_token,
                )

        await self.repository.delete_connection(connection.id)

    def _build_state(
        self,
        *,
        provider: IntegrationProvider,
        user_id: UUID,
        org_id: UUID,
    ) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "user_id": str(user_id),
            "org_id": str(org_id),
            "provider": provider.value,
            "jti": str(uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.STATE_TTL_SECONDS)).timestamp()),
        }
        return jwt.encode(payload, settings.secret_key, algorithm="HS256")

    @staticmethod
    def _verify_state(state: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                state,
                settings.secret_key,
                algorithms=["HS256"],
                options={"require": ["exp", "iat", "jti", "provider", "org_id", "user_id"]},
            )
        except jwt.PyJWTError as exc:
            raise ValueError("Invalid or expired OAuth state") from exc

    @staticmethod
    def _connection_values(
        *,
        provider: IntegrationProvider,
        org_id: UUID,
        user_id: UUID,
        tokens: dict[str, Any],
        realm_id: str | None = None,
        tenant_id: str | None = None,
        account_name: str | None = None,
    ) -> dict[str, Any]:
        expires_in = int(tokens.get("expires_in") or 3600)
        return {
            "org_id": org_id,
            "provider": provider,
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type"),
            "token_scope": tokens.get("scope"),
            "expires_at": datetime.now(UTC) + timedelta(seconds=expires_in),
            "realm_id": realm_id,
            "tenant_id": tenant_id,
            "account_name": account_name,
            "is_active": True,
            "last_error": None,
            "last_error_at": None,
            "error_count": 0,
            "health_status": "healthy",
            "sync_enabled": True,
            "sync_interval_mins": 60,
            "sync_from_date": None,
            "auto_analyze": True,
            "document_types_to_sync": [],
            "metadata": {},
            "connected_by": user_id,
            "updated_at": datetime.now(UTC),
        }
