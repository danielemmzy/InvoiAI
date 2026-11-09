from __future__ import annotations

"""Centralized API and platform error handling.

The application talks to several external/runtime systems (Supabase,
PostgREST/Storage, Redis, OpenAI, Stripe and generic HTTP providers).
Those failures must not be converted into random 400/401/500 responses at
individual call sites. This module normalizes them into one safe API shape
while keeping technical details in server logs.
"""

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.logging import logger


@dataclass(slots=True)
class ErrorDescriptor:
    status_code: int
    code: str
    message: str
    retryable: bool = False
    service: str | None = None
    details: dict[str, Any] | None = None


class AppError(Exception):
    """Safe application error intended for API/worker boundaries."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "APPLICATION_ERROR",
        status_code: int = 500,
        retryable: bool = False,
        service: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.service = service


class PlatformError(AppError):
    """An infrastructure/external-provider failure."""


def _exception_name(exc: BaseException) -> str:
    return type(exc).__name__.lower()


def _exception_module(exc: BaseException) -> str:
    return type(exc).__module__.lower()


def _status_from_exception(exc: BaseException) -> int | None:
    value = getattr(exc, "status_code", None)
    if isinstance(value, int) and 100 <= value <= 599:
        return value

    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int) and 100 <= value <= 599:
        return value

    return None


def classify_exception(exc: BaseException) -> ErrorDescriptor:
    """Map known runtime/provider exceptions to a stable public contract."""

    if isinstance(exc, AppError):
        return ErrorDescriptor(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            service=exc.service,
            details=None,
        )

    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            code = str(detail.get("code") or f"HTTP_{exc.status_code}")
            message = str(detail.get("message") or "Request could not be completed.")
            safe_keys = {"existing_document_id", "existing_file_name", "field", "resource"}
            details = {key: detail[key] for key in safe_keys if key in detail}
        elif isinstance(detail, str):
            details = None
            code = f"HTTP_{exc.status_code}"
            message = detail
        else:
            code = f"HTTP_{exc.status_code}"
            message = "Request could not be completed."
            details = None

        return ErrorDescriptor(
            status_code=exc.status_code,
            code=code,
            message=message,
            retryable=exc.status_code in {408, 425, 429} or exc.status_code >= 500,
            details=details,
        )

    module = _exception_module(exc)
    name = _exception_name(exc)
    status = _status_from_exception(exc)

    # Internal integration adapter failures. These already normalize provider
    # responses, so preserve their semantic status instead of returning 500.
    if module.startswith("app.integrations.base.exceptions"):
        if name == "tokenexpirederror":
            return ErrorDescriptor(
                401,
                "TOKEN_EXPIRED",
                "The integration session has expired. Please reconnect it.",
                False,
                "integration",
            )
        if name == "authorizationdeniederror":
            return ErrorDescriptor(
                403,
                "AUTHORIZATION_DENIED",
                "The integration provider denied access.",
                False,
                "integration",
            )
        if name == "notfounderror":
            return ErrorDescriptor(
                404,
                "REMOTE_RESOURCE_NOT_FOUND",
                "The requested provider resource was not found.",
                False,
                "integration",
            )
        if name == "ratelimiterror" or status == 429:
            return ErrorDescriptor(
                429,
                "PROVIDER_RATE_LIMITED",
                "The provider is rate limited. Please try again shortly.",
                True,
                "integration",
            )
        if status is not None and 400 <= status < 500:
            return ErrorDescriptor(
                502,
                "PROVIDER_REQUEST_REJECTED",
                "The external provider rejected the request.",
                False,
                "integration",
            )
        return ErrorDescriptor(
            503,
            "PROVIDER_UNAVAILABLE",
            "The external provider is temporarily unavailable. Please try again shortly.",
            True,
            "integration",
        )

    # OpenAI SDK/runtime failures.
    if module.startswith("openai") or "openai" in module:
        if "ratelimit" in name:
            return ErrorDescriptor(
                429,
                "AI_RATE_LIMITED",
                "The AI service is rate limited. Please try again shortly.",
                True,
                "openai",
            )
        if "timeout" in name:
            return ErrorDescriptor(
                504,
                "AI_PROVIDER_TIMEOUT",
                "The AI service took too long to respond. Please try again.",
                True,
                "openai",
            )
        if status == 429:
            return ErrorDescriptor(
                429,
                "AI_RATE_LIMITED",
                "The AI service is rate limited. Please try again shortly.",
                True,
                "openai",
            )
        if status is not None and 400 <= status < 500:
            return ErrorDescriptor(
                502,
                "AI_PROVIDER_ERROR",
                "The AI service rejected the request. Please try again.",
                True,
                "openai",
            )
        return ErrorDescriptor(
            503,
            "AI_PROVIDER_UNAVAILABLE",
            "The AI service is temporarily unavailable. Please try again shortly.",
            True,
            "openai",
        )

    # Redis / Upstash failures, including DNS failures such as getaddrinfo.
    if module.startswith("redis") or "redis" in module:
        return ErrorDescriptor(
            503,
            "REDIS_UNAVAILABLE",
            "The background infrastructure is temporarily unavailable. Please try again shortly.",
            True,
            "redis",
        )

    # Supabase Auth/Gotrue failures. AuthApiError does not consistently expose
    # its HTTP status on every installed client version, so credential/session
    # failures must also be recognized from the provider's error text.
    if module.startswith("gotrue") or module.startswith("supabase_auth"):
        message = str(exc).lower()
        expired_markers = (
            "token is expired",
            "jwt expired",
            "token expired",
            "session has expired",
            "session expired",
        )
        invalid_credential_markers = (
            "invalid jwt",
            "invalid token",
            "jwt signature",
            "token has invalid claims",
            "invalid authentication credentials",
            "invalid refresh token",
        )

        if any(marker in message for marker in expired_markers):
            return ErrorDescriptor(
                401,
                "TOKEN_EXPIRED",
                "Your session has expired. Please sign in again.",
                False,
                "supabase_auth",
            )

        if status in {400, 401, 403, 404, 422} or any(
            marker in message for marker in invalid_credential_markers
        ):
            return ErrorDescriptor(
                401,
                "AUTHENTICATION_FAILED",
                "Authentication could not be completed.",
                False,
                "supabase_auth",
            )

        if "timeout" in name or "timeout" in message:
            return ErrorDescriptor(
                504,
                "SUPABASE_AUTH_TIMEOUT",
                "Authentication service took too long to respond. Please try again.",
                True,
                "supabase_auth",
            )

        return ErrorDescriptor(
            503,
            "SUPABASE_AUTH_UNAVAILABLE",
            "Authentication service is temporarily unavailable. Please try again shortly.",
            True,
            "supabase_auth",
        )

    # Supabase/PostgREST/Storage SDK failures.
    if module.startswith("postgrest") or "postgrest" in module:
        return ErrorDescriptor(
            503,
            "DATABASE_UNAVAILABLE",
            "The database service is temporarily unavailable. Please try again shortly.",
            True,
            "supabase",
        )
    if module.startswith("storage3") or ("storage" in module and "supabase" in module):
        return ErrorDescriptor(
            503,
            "STORAGE_UNAVAILABLE",
            "Document storage is temporarily unavailable. Please try again shortly.",
            True,
            "supabase_storage",
        )
    if module.startswith("supabase") or "supabase" in module:
        return ErrorDescriptor(
            503,
            "SUPABASE_UNAVAILABLE",
            "A required Supabase service is temporarily unavailable. Please try again shortly.",
            True,
            "supabase",
        )

    # Stripe/payment-provider failures.
    if module.startswith("stripe") or "stripe" in module:
        if status == 429 or "ratelimit" in name:
            return ErrorDescriptor(
                429,
                "PAYMENT_PROVIDER_RATE_LIMITED",
                "The payment service is temporarily rate limited. Please try again shortly.",
                True,
                "stripe",
            )
        return ErrorDescriptor(
            502,
            "PAYMENT_PROVIDER_ERROR",
            "The payment service could not complete the request. Please try again.",
            True,
            "stripe",
        )

    # Generic HTTP/network failures. Keep technical details out of the API.
    if module.startswith("httpx") or module.startswith("httpcore"):
        if "timeout" in name:
            return ErrorDescriptor(
                504,
                "UPSTREAM_TIMEOUT",
                "An external service took too long to respond. Please try again.",
                True,
                "upstream",
            )
        return ErrorDescriptor(
            503,
            "UPSTREAM_UNAVAILABLE",
            "An external service is temporarily unavailable. Please try again shortly.",
            True,
            "upstream",
        )

    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return ErrorDescriptor(
            503,
            "PLATFORM_UNAVAILABLE",
            "A required platform service is temporarily unavailable. Please try again shortly.",
            True,
            "platform",
        )

    return ErrorDescriptor(
        500,
        "INTERNAL_SERVER_ERROR",
        "An unexpected error occurred. Please try again later.",
        False,
        None,
    )


def _payload(
    descriptor: ErrorDescriptor,
    *,
    error_id: str,
    request_id: str | None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "code": descriptor.code,
        "message": descriptor.message,
        "error_id": error_id,
        "retryable": descriptor.retryable,
    }
    if descriptor.service:
        detail["service"] = descriptor.service
    if descriptor.details:
        detail.update(descriptor.details)
    if request_id:
        detail["request_id"] = request_id
    return {"detail": detail}


def error_response(
    request: Request,
    exc: BaseException,
    *,
    force_log: bool = True,
    error_id: str | None = None,
) -> JSONResponse:
    """Build the single public error contract used by the API.

    ``error_id`` may be supplied by middleware so the same identifier is used
    for both the server log and the response. This prevents one failure from
    receiving two unrelated IDs when the middleware is the final safety net.
    """
    descriptor = classify_exception(exc)
    resolved_error_id = error_id or str(uuid4())
    request_id = request.headers.get("x-request-id")

    if force_log or descriptor.status_code >= 500:
        logger.error(
            "api_error",
            error_id=resolved_error_id,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            error_type=type(exc).__name__,
            error_code=descriptor.code,
            service=descriptor.service,
            status_code=descriptor.status_code,
            retryable=descriptor.retryable,
            exc_info=descriptor.status_code >= 500,
        )

    return JSONResponse(
        status_code=descriptor.status_code,
        content=_payload(descriptor, error_id=resolved_error_id, request_id=request_id),
        headers={"X-Error-ID": resolved_error_id},
    )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    return error_response(request, exc, force_log=False)


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    descriptor = ErrorDescriptor(
        422,
        "VALIDATION_ERROR",
        "The request contains invalid or missing fields.",
        False,
        None,
    )
    error_id = str(uuid4())
    logger.info(
        "request_validation_error",
        error_id=error_id,
        method=request.method,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=422,
        content=_payload(descriptor, error_id=error_id, request_id=request.headers.get("x-request-id")),
        headers={"X-Error-ID": error_id},
    )


async def handle_rate_limit_error(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    descriptor = ErrorDescriptor(
        429,
        "RATE_LIMITED",
        "Too many requests. Please wait a moment and try again.",
        True,
        None,
    )
    error_id = str(uuid4())
    logger.warning(
        "rate_limit_exceeded",
        error_id=error_id,
        method=request.method,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=429,
        content=_payload(descriptor, error_id=error_id, request_id=request.headers.get("x-request-id")),
        headers={"Retry-After": "60", "X-Error-ID": error_id},
    )


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(request, exc)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(request, exc)


def safe_user_message(exc: BaseException) -> str:
    """Return the same safe message used by the API for worker/user state."""
    return classify_exception(exc).message


def platform_error(exc: BaseException) -> PlatformError | None:
    """Convert a provider/infrastructure failure into ``PlatformError``.

    Only server-side/retryable failures are converted here. Client/domain
    errors (including Supabase invalid credentials) must return ``None`` so
    authentication and other callers can preserve their own 401/4xx semantics.
    """
    descriptor = classify_exception(exc)

    if descriptor.status_code < 500:
        return None

    return PlatformError(
        descriptor.message,
        code=descriptor.code,
        status_code=descriptor.status_code,
        retryable=descriptor.retryable,
        service=descriptor.service,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(RateLimitExceeded, handle_rate_limit_error)
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
