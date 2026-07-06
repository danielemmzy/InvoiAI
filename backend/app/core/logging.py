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

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.debug else logging.INFO,
    )


logger = structlog.get_logger()