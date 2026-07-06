from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import logger


class ExceptionLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        try:
            return await call_next(request)

        except Exception:

            logger.exception(
                "Unhandled exception",
                method=request.method,
                path=request.url.path,
            )

            raise