from __future__ import annotations

"""
Central OAuth token encryption/decryption service.

Raw OAuth token bytes are handled only here.

Cipher:
    AES-256-GCM

Stored format:
    v1.<base64url nonce>.<base64url ciphertext+tag>

The encryption key is supplied through TOKEN_ENCRYPTION_KEY as a
base64-encoded 32-byte value. Never generate a key at runtime in
production; losing the key makes existing integration credentials
undecryptable.
"""

import base64
import binascii
from copy import copy
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings
from app.core.enum.database import IntegrationProvider
from app.models.domain.integration import IntegrationConnection
from app.repositories.integration.integration_repository import (
    IntegrationConnectionRepository,
)


class TokenService:
    """Owns encryption, decryption, and provider token hydration."""

    VERSION = "v1"
    NONCE_SIZE = 12
    KEY_SIZE = 32

    def __init__(
        self,
        *,
        repository: IntegrationConnectionRepository,
    ) -> None:
        self.repository = repository
        self._aes = AESGCM(self._load_key())

    @classmethod
    def _load_key(cls) -> bytes:
        raw = settings.token_encryption_key.strip()
        if not raw:
            raise RuntimeError(
                "TOKEN_ENCRYPTION_KEY is required for OAuth token storage."
            )

        try:
            padded = raw + ("=" * (-len(raw) % 4))
            key = base64.urlsafe_b64decode(padded.encode("ascii"))
        except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
            raise RuntimeError(
                "TOKEN_ENCRYPTION_KEY must be a base64url-encoded 32-byte key."
            ) from exc

        if len(key) != cls.KEY_SIZE:
            raise RuntimeError(
                "TOKEN_ENCRYPTION_KEY must decode to exactly 32 bytes."
            )

        return key

    # =========================================================
    # Encryption primitives
    # =========================================================

    def encrypt(self, token: str) -> str:
        if not token:
            raise ValueError("Cannot encrypt an empty OAuth token.")

        import os

        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._aes.encrypt(
            nonce,
            token.encode("utf-8"),
            None,
        )

        return ".".join(
            (
                self.VERSION,
                self._b64(nonce),
                self._b64(ciphertext),
            )
        )

    def decrypt(self, value: str) -> str:
        if not value:
            raise ValueError("Cannot decrypt an empty OAuth token.")

        parts = value.split(".")
        if len(parts) != 3 or parts[0] != self.VERSION:
            raise ValueError("OAuth token is not stored in the supported encrypted format.")

        try:
            nonce = self._b64decode(parts[1])
            ciphertext = self._b64decode(parts[2])
            plaintext = self._aes.decrypt(nonce, ciphertext, None)
        except (ValueError, binascii.Error, InvalidTag) as exc:
            raise ValueError("OAuth token decryption failed.") from exc

        return plaintext.decode("utf-8")

    @staticmethod
    def _b64(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    @staticmethod
    def _b64decode(value: str) -> bytes:
        return base64.urlsafe_b64decode(
            value + "=" * (-len(value) % 4)
        )

    def is_encrypted(self, value: str | None) -> bool:
        return bool(value) and value.startswith(f"{self.VERSION}.")

    # =========================================================
    # Persistence boundary
    # =========================================================

    def encrypt_token_fields(
        self,
        *,
        access_token: str,
        refresh_token: str | None,
    ) -> dict[str, str | None]:
        return {
            "access_token": (
                access_token
                if self.is_encrypted(access_token)
                else self.encrypt(access_token)
            ),
            "refresh_token": (
                None
                if refresh_token is None
                else (
                    refresh_token
                    if self.is_encrypted(refresh_token)
                    else self.encrypt(refresh_token)
                )
            ),
        }

    def decrypt_connection(
        self,
        connection: IntegrationConnection,
    ) -> IntegrationConnection:
        """Return a copy with plaintext tokens for an immediate API operation."""
        hydrated = copy(connection)
        hydrated.access_token = self.decrypt(connection.access_token)

        if connection.refresh_token:
            hydrated.refresh_token = self.decrypt(connection.refresh_token)

        return hydrated

    async def get_connection(
        self,
        connection_id: UUID,
    ) -> IntegrationConnection | None:
        connection = await self.repository.get_connection(connection_id)
        if connection is None:
            return None
        return self.decrypt_connection(connection)

    async def get_org_connection(
        self,
        *,
        org_id: UUID,
        provider: IntegrationProvider,
    ) -> IntegrationConnection | None:
        connection = await self.repository.get_org_connection(org_id, provider)
        if connection is None:
            return None
        return self.decrypt_connection(connection)

    async def get_access_token(
        self,
        *,
        org_id: UUID,
        provider: IntegrationProvider,
    ) -> str:
        connection = await self.get_org_connection(
            org_id=org_id,
            provider=provider,
        )
        if connection is None or not connection.is_active:
            raise ValueError("Integration connection is not active.")

        return connection.access_token

    async def get_refresh_token(
        self,
        *,
        org_id: UUID,
        provider: IntegrationProvider,
    ) -> str:
        connection = await self.get_org_connection(
            org_id=org_id,
            provider=provider,
        )
        if connection is None or not connection.is_active:
            raise ValueError("Integration connection is not active.")
        if not connection.refresh_token:
            raise ValueError("Integration has no refresh token.")

        return connection.refresh_token

    async def store_tokens(
        self,
        *,
        connection_id: UUID,
        access_token: str,
        refresh_token: str | None,
        expires_at: Any,
    ) -> IntegrationConnection | None:
        encrypted = self.encrypt_token_fields(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        return await self.repository.update_tokens(
            connection_id,
            access_token=encrypted["access_token"],
            refresh_token=encrypted["refresh_token"],
            expires_at=expires_at,
        )

    async def refresh_connection(
        self,
        *,
        connection: IntegrationConnection,
        oauth,
    ) -> IntegrationConnection | None:
        """Refresh using decrypted credentials, then immediately re-encrypt them."""
        hydrated = self.decrypt_connection(connection)

        if not hydrated.refresh_token:
            raise ValueError("Integration has no refresh token.")

        tokens = await oauth.refresh_token(
            refresh_token=hydrated.refresh_token,
        )

        from datetime import UTC, datetime, timedelta

        expires_at = datetime.now(UTC) + timedelta(
            seconds=int(tokens.get("expires_in") or 3600)
        )

        return await self.store_tokens(
            connection_id=connection.id,
            access_token=tokens["access_token"],
            refresh_token=tokens.get(
                "refresh_token",
                hydrated.refresh_token,
            ),
            expires_at=expires_at.isoformat(),
        )
