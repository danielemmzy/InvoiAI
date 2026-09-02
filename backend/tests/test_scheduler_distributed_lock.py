import pytest

from app2.core.distributed_lock import DistributedLock


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.ttls[key] = ex
        return True

    async def eval(self, script, numkeys, key, token, ttl=None):
        if script.find("del") >= 0:
            if self.values.get(key) == token:
                del self.values[key]
                return 1
            return 0
        if self.values.get(key) == token:
            self.ttls[key] = ttl
            return 1
        return 0


@pytest.mark.asyncio
async def test_distributed_lock_allows_single_owner(monkeypatch):
    fake = FakeRedis()

    async def get_fake_redis():
        return fake

    monkeypatch.setattr("app.core.distributed_lock.get_redis", get_fake_redis)
    monkeypatch.setattr("app.core.distributed_lock.settings.scheduler_lock_enabled", True)

    first = DistributedLock(key="test:lock", ttl_seconds=30)
    second = DistributedLock(key="test:lock", ttl_seconds=30)

    assert await first.acquire() is True
    assert await second.acquire() is False

    assert await first.refresh() is True
    await first.release()
    assert await second.acquire() is True
    await second.release()
