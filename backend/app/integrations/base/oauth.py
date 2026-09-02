from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class BaseOAuthProvider(ABC):
    """
    Base OAuth implementation.

    Every provider implements the same interface.

    QuickBooks

    Xero

    Google

    Microsoft

    Dropbox

    etc.
    """

    @abstractmethod
    async def authorization_url(
        self,
        *,
        state: str,
    ) -> str:
        """
        Returns provider authorization URL.
        """

    @abstractmethod
    async def exchange_code(
        self,
        *,
        code: str,
    ) -> dict:
        """
        Exchanges authorization code
        for access + refresh token.
        """

    @abstractmethod
    async def refresh_token(
        self,
        *,
        refresh_token: str,
    ) -> dict:
        """
        Refresh expired token.
        """

    @abstractmethod
    async def revoke(
        self,
        *,
        access_token: str,
    ) -> None:
        """
        Disconnect integration.
        """