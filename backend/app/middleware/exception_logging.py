from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.error_handler import error_response


class ExceptionLoggingMiddleware(BaseHTTPMiddleware):
    """Final safety net for unexpected API errors.

    Exception handlers normally process application exceptions. Middleware
    exceptions, however, can bypass FastAPI's exception-handler registry.
    This middleware therefore delegates to the same centralized formatter
    instead of returning a second, incompatible 500 response shape.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            return error_response(request, exc)
