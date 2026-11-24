"""============================================================
app/core/db.py

Blocking database offload.

Supabase's Python client is synchronous. Calling it directly from an
``async def`` endpoint blocks the event loop for the whole round trip, so
concurrent requests queue behind one another even though the backend is doing
nothing but waiting on the network.

Everything that performs database I/O from an async path goes through this
module:

    response = await execute(query)              # one query
    rows, count = await gather_rows(query)       # several independent queries

The work runs in a *bounded* thread pool. Threads are only created up to
``settings.db_thread_pool_size``; the pool is created lazily and shut down with
the application lifespan, so a burst of traffic cannot spawn unbounded threads.
============================================================
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Awaitable, TypeVar

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    """Return the lazily created, process-wide database thread pool."""

    global _executor

    if _executor is None:
        max_workers = max(4, int(settings.db_thread_pool_size))
        _executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="supabase-db",
        )
        logger.info("Database thread pool initialized (max_workers=%s).", max_workers)

    return _executor


async def run_db(func, /, *args, **kwargs) -> Any:
    """Run a blocking database helper in the bounded pool.

    Use for repository methods and any other callable that performs synchronous
    Supabase I/O.
    """

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _get_executor(),
        partial(func, *args, **kwargs),
    )


async def execute(query):
    """Execute an already-built Supabase query builder off the event loop.

    Building the query does no I/O, so only ``execute()`` needs offloading:

        rows = await execute(self.table().select("*").eq("org_id", str(org_id)))
    """

    return await run_db(query.execute)


async def gather_queries(*queries) -> list[Any]:
    """Execute independent query builders concurrently.

    Only use this for queries that do not depend on one another's results and
    belong to the same request/organization.
    """

    return list(await asyncio.gather(*(execute(query) for query in queries)))


async def gather_calls(*calls: Awaitable[T]) -> list[T]:
    """Convenience wrapper so call sites read uniformly with ``gather_queries``."""

    return list(await asyncio.gather(*calls))


def shutdown_executor() -> None:
    """Stop accepting work and drain the pool. Called on application shutdown."""

    global _executor

    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None
        logger.info("Database thread pool shut down.")
