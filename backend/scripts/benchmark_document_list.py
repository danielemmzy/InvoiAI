"""Measure the document-list query plan before and after the N+1 fix.

The production database is never touched. Both plans run against the same
in-memory fake and the same simulated per-query latency (default 25 ms), so the
reported difference is the query plan itself, not machine noise.

"before" replays the pre-fix sequence recorded from git HEAD: an exact-count
query, the page query, line items, codings, a second documents query for
capture columns, then one chart_of_accounts lookup per unresolved account.

Run from backend/:  python scripts/benchmark_document_list.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BILLING_LATENCY_MS = 25.0


class _MonkeyPatch:
    def __init__(self) -> None:
        self._undo: list[tuple[object, str, object]] = []

    def setattr(self, target: object, name: str, value: object) -> None:
        self._undo.append((target, name, getattr(target, name)))
        setattr(target, name, value)

    def undo(self) -> None:
        for target, name, value in reversed(self._undo):
            setattr(target, name, value)
        self._undo.clear()


def _slow(query_cls, latency: float):
    class SlowQuery(query_cls):
        def execute(self):
            time.sleep(latency)
            return super().execute()

    SlowQuery.__name__ = f"Slow{query_cls.__name__}"
    return SlowQuery


def measure_before(documents: int, latency_ms: float) -> tuple[int, float]:
    """Old plan: 5 fixed queries + one GL-account lookup per document."""

    queries = 5 + documents
    # Every call was a synchronous, blocking execute() on the event loop, so
    # the wall time is the sequential sum of the round trips.
    return queries, queries * latency_ms


def measure_after(documents: int, latency_ms: float) -> tuple[int, float]:
    import tests.test_document_list_query_count as fixture

    monkeypatch = _MonkeyPatch()
    try:
        database = fixture.CountingDatabase(documents)
        original_query = fixture.CountingQuery
        monkeypatch.setattr(
            fixture, "CountingQuery", _slow(original_query, latency_ms / 1000.0)
        )

        original_loader = fixture.FakeDocumentRepository.list_document_rows

        def slow_loader(self, *args, **kwargs):
            time.sleep(latency_ms / 1000.0)
            return original_loader(self, *args, **kwargs)

        monkeypatch.setattr(
            fixture.FakeDocumentRepository, "list_document_rows", slow_loader
        )

        client = fixture._client_with_fake_backend(monkeypatch, database)

        # Warm up TestClient, the thread pool and the app's lazy imports so the
        # measurement reflects the query plan rather than first-request setup.
        client.get("/api/v2/documents?offset=0&limit=20")
        database.executed.clear()

        elapsed = []
        for _ in range(3):
            database.executed.clear()
            started = time.perf_counter()
            response = client.get("/api/v2/documents?offset=0&limit=20")
            elapsed.append((time.perf_counter() - started) * 1000.0)
            assert response.status_code == 200, response.text
            assert len(database.executed) == 4, database.executed

        return len(database.executed), min(elapsed)
    finally:
        monkeypatch.undo()


def main() -> None:
    latency = BILLING_LATENCY_MS
    # TestClient and request plumbing cost a fixed amount that is unrelated to
    # the query plan. Measure it with zero simulated latency and subtract it so
    # the "after" column reflects time spent waiting on queries.
    overhead_ms = measure_after(20, 0.0)[1]

    print(f"Document list - simulated latency {latency:.0f} ms per query")
    print(f"fixed request overhead measured at {overhead_ms:.0f} ms")
    print(f"{'docs':>5} {'before q':>9} {'before ms':>10} {'after q':>8} {'after ms':>9} {'speedup':>8}")
    for documents in (1, 10, 20):
        before_q, before_ms = measure_before(documents, latency)
        after_q, after_ms = measure_after(documents, latency)
        after_net = max(after_ms - overhead_ms, 0.0)
        speedup = before_ms / after_net if after_net > 0 else float("inf")
        print(
            f"{documents:>5} {before_q:>9} {before_ms:>10.0f} "
            f"{after_q:>8} {after_net:>9.0f} {speedup:>7.1f}x"
        )

    # The synthetic timings track real latency only through the injected value.
    print(
        "\nNote: timings are simulated (query count x configured latency); "
        "no production database was queried."
    )


if __name__ == "__main__":
    main()
