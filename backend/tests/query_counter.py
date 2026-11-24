"""Supabase round-trip counter used by performance regression tests.

Every Supabase PostgREST call is a network round trip made through
``client.table(name)....execute()``. This module wraps a client so each
``execute()`` is recorded against the table it targeted, which lets tests assert
that the number of queries stays constant as the number of records grows.

The wrapper only proxies an existing client: it never changes query semantics.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class QueryRecord:
    """One observed ``execute()`` call."""

    table: str
    duration_ms: float


@dataclass
class QueryCounter:
    """Records every query executed through a wrapped client."""

    records: list[QueryRecord] = field(default_factory=list)

    def record(self, table: str, duration_ms: float) -> None:
        self.records.append(QueryRecord(table=table, duration_ms=duration_ms))

    # -- assertions -----------------------------------------------------
    def reset(self) -> None:
        self.records.clear()

    @property
    def total(self) -> int:
        return len(self.records)

    @property
    def tables(self) -> Counter[str]:
        return Counter(record.table for record in self.records)

    def table_count(self, table: str) -> int:
        return self.tables.get(table, 0)

    def summary(self) -> str:
        parts = [f"{table}={count}" for table, count in sorted(self.tables.items())]
        return f"total={self.total} " + " ".join(parts)


class _CountingQuery:
    """Proxy for a PostgREST query builder that records ``execute()``."""

    __slots__ = ("_builder", "_counter", "_table")

    def __init__(self, builder, counter: QueryCounter, table: str) -> None:
        object.__setattr__(self, "_builder", builder)
        object.__setattr__(self, "_counter", counter)
        object.__setattr__(self, "_table", table)

    def __getattr__(self, name: str):
        attribute = getattr(self._builder, name)
        if not callable(attribute):
            return attribute

        def proxy(*args, **kwargs):
            result = attribute(*args, **kwargs)
            # PostgREST builders are immutable: each chained call returns a new
            # builder. Re-wrap anything that can still be executed so the final
            # ``execute()`` is observed regardless of chain length.
            if hasattr(result, "execute"):
                return _CountingQuery(result, self._counter, self._table)
            return result

        return proxy

    def execute(self, *args, **kwargs):
        started = time.perf_counter()
        try:
            return self._builder.execute(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._counter.record(self._table, elapsed_ms)


class _CountingAuth:
    """Proxy for ``client.auth`` that counts auth round trips."""

    __slots__ = ("_auth", "_counter")

    def __init__(self, auth, counter: QueryCounter) -> None:
        object.__setattr__(self, "_auth", auth)
        object.__setattr__(self, "_counter", counter)

    def __getattr__(self, name: str):
        attribute = getattr(self._auth, name)
        if not callable(attribute):
            return attribute

        def proxy(*args, **kwargs):
            started = time.perf_counter()
            try:
                return attribute(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - started) * 1000
                self._counter.record(f"auth.{name}", elapsed_ms)

        return proxy


class CountingClient:
    """Supabase client wrapper that records the number of round trips."""

    __slots__ = ("_client", "counter")

    def __init__(self, client, counter: QueryCounter | None = None) -> None:
        object.__setattr__(self, "_client", client)
        object.__setattr__(self, "counter", counter or QueryCounter())

    def __getattr__(self, name: str):
        attribute = getattr(self._client, name)
        if name == "auth":
            return _CountingAuth(attribute, self.counter)
        return attribute

    def table(self, name: str):
        return _CountingQuery(self._client.table(name), self.counter, name)


def instrument_client(client, counter: QueryCounter) -> None:
    """Instrument an existing client instance in place.

    Repositories hold the shared service client directly, so wrapping the
    factory is not enough: the instance's own ``table`` and auth methods must be
    observed. Instance attributes shadow the class methods, so every caller of
    this client - including code that captured it before instrumentation - is
    counted.
    """

    original_table = client.table

    def table(name: str):
        return _CountingQuery(original_table(name), counter, name)

    client.table = table

    auth = getattr(client, "auth", None)
    if auth is not None:
        auth.get_user = _CountingAuth(auth, counter).__getattr__("get_user")
