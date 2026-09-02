from __future__ import annotations


class IntegrationError(Exception):
    """
    Base exception for every integration.

    All provider-specific exceptions should inherit from this.
    """


class OAuthError(IntegrationError):
    """
    OAuth authentication failed.
    """


class TokenExpiredError(OAuthError):
    """
    Access token expired and could not be refreshed.
    """


class RefreshTokenError(OAuthError):
    """
    Refresh token is invalid or revoked.
    """


class AuthorizationDeniedError(OAuthError):
    """
    User denied authorization.
    """


class APIError(IntegrationError):
    """
    Provider returned an API error.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: dict | None = None,
    ):

        super().__init__(message)

        self.status_code = status_code
        self.payload = payload or {}


class RateLimitError(APIError):
    """
    Provider rate limit exceeded.
    """


class ValidationError(APIError):
    """
    Invalid payload sent to provider.
    """


class NotFoundError(APIError):
    """
    Remote resource not found.
    """


class SyncError(IntegrationError):
    """
    Synchronization failed.
    """


class MappingError(IntegrationError):
    """
    Failed mapping provider data into domain model.
    """