import time

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import logger
from app.core.observability import record_api_request


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        start = time.perf_counter()

        response = await call_next(request)

        duration = round((time.perf_counter() - start) * 1000, 2)

        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)

        record_api_request(
            method=request.method,
            route=route_path,
            status=response.status_code,
            duration_ms=duration,
        )

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration,
            client_ip=request.client.host if request.client else "unknown",
        )

        return response
