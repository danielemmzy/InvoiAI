from __future__ import annotations

from abc import ABC
from abc import abstractmethod
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
    """

    def __init__(self) -> None:

        self.timeout = DEFAULT_TIMEOUT

        self.max_retries = MAX_RETRIES

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
                ) as client:

                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        **kwargs,
                    )

                self._raise_for_status(response)

                if not response.content:
                    return {}

                return response.json()

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
            ) as exc:

                last_error = exc

                if attempt == self.max_retries - 1:
                    raise APIError(
                        "Network request failed."
                    ) from exc

        raise APIError(
            str(last_error),
        )

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