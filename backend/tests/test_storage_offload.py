"""Supabase Storage calls are blocking HTTP; they must run off the event loop.

The Storage SDK exposes synchronous methods. Awaiting them directly inside an
``async def`` kept the whole event loop blocked for the duration of every
upload, download, delete, signed-URL and existence check.
"""

import threading
import time

import pytest

from app.core.error_handler import PlatformError
from app.services.storage.storage import StorageService

DELAY = 0.05


class FakeBucket:
    def __init__(self, delay=DELAY, error=None):
        self.delay = delay
        self.error = error
        self.calls: list[str] = []
        self.thread_ids: list[int] = []

    def _run(self, name):
        self.thread_ids.append(threading.get_ident())
        time.sleep(self.delay)
        if self.error is not None:
            raise self.error
        self.calls.append(name)

    def download(self, path):
        self._run("download")
        return b"stored-bytes"

    def upload(self, path, content, options):
        self._run("upload")
        return None

    def remove(self, paths):
        self._run("remove")
        return None

    def create_signed_url(self, path, expires_in):
        self._run("create_signed_url")
        return {"signedURL": f"https://storage.test/{path}"}

    def list(self, folder):
        self._run("list")
        # The caller checks the object's file name inside its parent folder.
        return [{"name": "doc.pdf"}, {"name": "other.pdf"}]


class FakeStorageApi:
    def __init__(self, bucket):
        self.bucket = bucket
        self.from_calls: list[str] = []

    def from_(self, name):
        self.from_calls.append(name)
        return self.bucket


class FakeClient:
    def __init__(self, bucket):
        self.storage = FakeStorageApi(bucket)


def _service(bucket):
    return StorageService(client=FakeClient(bucket))


@pytest.mark.asyncio
async def test_uploads_run_off_the_event_loop_thread():
    bucket = FakeBucket()
    service = _service(bucket)
    loop_thread = threading.get_ident()

    await service.upload_document(
        path="org/inv.pdf", content=b"x", content_type="application/pdf"
    )

    # The blocking SDK call must happen on a pool thread, not the loop thread.
    assert bucket.calls == ["upload"]
    assert bucket.thread_ids
    assert loop_thread not in bucket.thread_ids


@pytest.mark.asyncio
async def test_download_delete_signed_url_and_exists_stay_off_the_loop():
    bucket = FakeBucket(delay=0)
    service = _service(bucket)

    assert await service.download_document("org/doc.pdf") == b"stored-bytes"
    await service.delete_document("org/doc.pdf")
    assert (
        await service.create_signed_url(path="org/doc.pdf", expires_in=60)
        == "https://storage.test/org/doc.pdf"
    )
    assert await service.exists("org/doc.pdf") is True
    assert bucket.calls == ["download", "remove", "create_signed_url", "list"]
    # Every operation is executed on a worker thread, never the loop thread.
    loop_thread = threading.get_ident()
    assert bucket.thread_ids
    assert loop_thread not in bucket.thread_ids


@pytest.mark.asyncio
async def test_storage_errors_keep_their_platform_error_contract():
    bucket = FakeBucket(delay=0, error=RuntimeError("bucket offline"))
    service = _service(bucket)

    with pytest.raises(PlatformError) as raised:
        await service.upload_document(
            path="org/doc.pdf", content=b"x", content_type="application/pdf"
        )

    assert raised.value.code == "STORAGE_UNAVAILABLE"
    assert raised.value.status_code == 503
    # Errors must not be silently swallowed or turned into a different type.
    assert isinstance(raised.value.__cause__, RuntimeError)
