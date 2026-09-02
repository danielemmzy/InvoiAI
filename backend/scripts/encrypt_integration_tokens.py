"""
One-time migration for existing plaintext integration OAuth tokens.

Before running:
    1. Set TOKEN_ENCRYPTION_KEY to a stable base64url-encoded 32-byte key.
    2. Ensure the service-role Supabase credentials are configured.
    3. Back up integration_connections.

This script is intentionally explicit and idempotent: already encrypted
tokens are skipped.
"""

from __future__ import annotations

import asyncio

from app2.core.container import get_container


async def main() -> None:
    container = get_container()
    token_service = container.token_service
    repository = container.integration_repository

    response = (
        repository.table()
        .select("id, access_token, refresh_token")
        .execute()
    )

    rows = response.data or []
    migrated = 0
    skipped = 0

    for row in rows:
        access_token = row.get("access_token")
        refresh_token = row.get("refresh_token")

        if token_service.is_encrypted(access_token):
            skipped += 1
            continue

        if not access_token:
            raise RuntimeError(
                f"Connection {row['id']} has no access token."
            )

        encrypted = token_service.encrypt_token_fields(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        repository.table().update(
            encrypted,
        ).eq(
            "id",
            row["id"],
        ).execute()

        migrated += 1

    print(
        f"Integration token migration complete: "
        f"{migrated} migrated, {skipped} already encrypted."
    )


if __name__ == "__main__":
    asyncio.run(main())
