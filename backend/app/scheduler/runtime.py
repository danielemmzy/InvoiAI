from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.distributed_lock import DistributedLock
from app.scheduler.periodic_jobs import cron

logger = logging.getLogger(__name__)


class CronRuntime:
    """Runs registered cron jobs with a Redis singleton lock per job.

    The lock prevents duplicate execution when the API is deployed with
    multiple Uvicorn/Gunicorn workers or multiple application replicas.
    """

    def __init__(self, poll_seconds: float = 1.0) -> None:
        self.poll_seconds = poll_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    async def _keep_lock_alive(self, lock: DistributedLock) -> None:
        interval = max(1.0, settings.scheduler_lock_ttl_seconds / 3)
        while True:
            await asyncio.sleep(interval)
            if not await lock.refresh():
                logger.warning("Lost scheduler lock: %s", lock.key)
                return

    async def _run_job(self, job) -> None:
        lock = DistributedLock(key=f"invoiai:scheduler:lock:{job.name}")
        acquired = await lock.acquire()
        if not acquired:
            logger.debug("Scheduler lock busy or Redis unavailable: %s", job.name)
            return

        heartbeat = asyncio.create_task(
            self._keep_lock_alive(lock),
            name=f"scheduler-lock-heartbeat:{job.name}",
        )
        try:
            await job.worker()
        except Exception:
            logger.exception("Scheduled worker failed: %s", job.name)
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            await lock.release()

    async def _loop(self) -> None:
        while self._running:
            for job in cron.due():
                await self._run_job(job)
            await asyncio.sleep(self.poll_seconds)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="invoiai-cron-runtime")
        logger.info("V2 cron runtime started")

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        logger.info("V2 cron runtime stopped")


cron_runtime = CronRuntime()
