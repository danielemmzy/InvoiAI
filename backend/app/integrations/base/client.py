from __future__ import annotations

import asyncio
from abc import ABC
from abc import abstractmethod
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.integrations.base.constants import (
    BACKOFF_SECONDS,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
)
from app.integrations.base.exceptions import (
    APIError,
    AuthorizationDeniedError,
    NotFoundError,
    RateLimitError,
    TokenExpiredError,
)


class BaseAPIClient(ABC):
    """
    Base HTTP client for every integration provider.

    Responsibilities
    ----------------
    • Authenticated requests
    • Retry handling
    • Error normalization
    • Shared HTTP client

    No provider-specific logic.

    Retry policy (shared by every provider):
    • 429 — back off using `Retry-After` when present, then retry.
    • 5xx — retry with bounded exponential backoff.
    • Timeout/network error — retry with bounded exponential backoff.
    • 4xx (except 429) — stop immediately; the request is not idempotent-safe.
    """

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Any | None = None,
    ) -> None:

        self.timeout = DEFAULT_TIMEOUT

        self.max_retries = MAX_RETRIES

        # Injected by the provider-contract test harness. Production
        # callers never pass these; httpx builds its normal transport.
        self._transport = transport
        self._sleep = sleep or asyncio.sleep

    # =====================================================
    # Provider configuration
    # =====================================================

    @property
    @abstractmethod
    def base_url(self) -> str:
        """
        Provider base URL.
        """

    @abstractmethod
    async def access_token(self) -> str:
        """
        Return a valid access token.

        Provider is responsible for refreshing
        expired tokens before returning.
        """

    # =====================================================
    # Headers
    # =====================================================

    async def headers(self) -> dict[str, str]:

        token = await self.access_token()

        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # =====================================================
    # HTTP Methods
    # =====================================================

    async def get(
        self,
        endpoint: str,
        *,
        params: dict | None = None,
    ) -> dict:

        return await self._request(
            "GET",
            endpoint,
            params=params,
        )

    async def post(
        self,
        endpoint: str,
        *,
        json: dict | None = None,
    ) -> dict:

        return await self._request(
            "POST",
            endpoint,
            json=json,
        )

    async def put(
        self,
        endpoint: str,
        *,
        json: dict | None = None,
    ) -> dict:

        return await self._request(
            "PUT",
            endpoint,
            json=json,
        )

    async def patch(
        self,
        endpoint: str,
        *,
        json: dict | None = None,
    ) -> dict:

        return await self._request(
            "PATCH",
            endpoint,
            json=json,
        )

    async def delete(
        self,
        endpoint: str,
    ) -> dict:

        return await self._request(
            "DELETE",
            endpoint,
        )

    # =====================================================
    # Request
    # =====================================================

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict:

        url = f"{self.base_url}{endpoint}"

        headers = await self.headers()

        last_error: Exception | None = None

        for attempt in range(self.max_retries):

            try:

                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    transport=self._transport,
                ) as client:

                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        **kwargs,
                    )

                if 200 <= response.status_code < 300:

                    if not response.content:
                        return {}

                    return response.json()

                if response.status_code == 429:

                    if attempt == self.max_retries - 1:
                        self._raise_for_status(response)

                    await self._sleep(
                        self._retry_after_seconds(response, attempt)
                    )
                    continue

                if response.status_code >= 500:

                    if attempt == self.max_retries - 1:
                        self._raise_for_status(response)

                    await self._sleep(self._backoff_seconds(attempt))
                    continue

                # Any other 4xx is deterministic; retrying cannot help.
                self._raise_for_status(response)

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
            ) as exc:

                last_error = exc

                if attempt == self.max_retries - 1:
                    raise APIError(
                        "Network request failed."
                    ) from exc

                await self._sleep(self._backoff_seconds(attempt))

        raise APIError(
            str(last_error),
        )

    # =====================================================
    # Retry helpers
    # =====================================================

    def _backoff_seconds(self, attempt: int) -> float:
        """Bounded exponential backoff: 2s, 4s, 8s, ... capped at 30s."""
        return min(BACKOFF_SECONDS * (2 ** attempt), 30)

    def _retry_after_seconds(self, response: httpx.Response, attempt: int) -> float:
        """Honor `Retry-After` as seconds or an HTTP date; fall back to backoff."""
        value = response.headers.get("Retry-After")
        if not value:
            return self._backoff_seconds(attempt)

        value = value.strip()

        try:
            return max(0.0, float(value))
        except ValueError:
            pass

        try:
            from datetime import UTC, datetime

            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            return max(0.0, (when - datetime.now(UTC)).total_seconds())
        except (TypeError, ValueError):
            return self._backoff_seconds(attempt)

    # =====================================================
    # Error handling
    # =====================================================

    def _raise_for_status(
        self,
        response: httpx.Response,
    ) -> None:

        code = response.status_code

        payload = {}

        try:
            payload = response.json()
        except Exception:
            pass

        if 200 <= code < 300:
            return

        if code == 401:

            raise TokenExpiredError(
                "Access token expired."
            )

        if code == 403:

            raise AuthorizationDeniedError(
                "Authorization denied."
            )

        if code == 404:

            raise NotFoundError(
                "Resource not found.",
                status_code=code,
                payload=payload,
            )

        if code == 429:

            raise RateLimitError(
                "Rate limit exceeded.",
                status_code=code,
                payload=payload,
            )

        raise APIError(
            f"Provider returned HTTP {code}",
            status_code=code,
            payload=payload,
        )
