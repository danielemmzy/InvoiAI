import logging
import sys

import structlog
from app.core.config import settings
from asgi_correlation_id import correlation_id


def configure_logging():
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    def add_request_id(_, __, event_dict):
        event_dict["request_id"] = correlation_id.get() or "-"
        return event_dict

    shared_processors = [
        add_request_id,
        structlog.stdlib.add_log_level,
        timestamper,
    ]

    if settings.debug:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Application logging level.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.debug else logging.INFO,
    )

    # -------------------------------------------------------------------------
    # Silence noisy third-party protocol/debug loggers.
    #
    # HTTPX / HTTPcore / HPACK can produce enormous amounts of DEBUG output
    # when the root logger is running at DEBUG. Keep them at WARNING so that
    # real connection/request problems are still visible.
    # -------------------------------------------------------------------------
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)
    logging.getLogger("google.auth").setLevel(logging.WARNING)
    logging.getLogger("google.api_core").setLevel(logging.WARNING)
    logging.getLogger("grpc").setLevel(logging.WARNING)

    # Optional: keep Uvicorn useful without its internal debug noise.
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    # Keep asyncio from becoming excessively verbose in debug mode.
    logging.getLogger("asyncio").setLevel(logging.WARNING)


logger = structlog.get_logger()