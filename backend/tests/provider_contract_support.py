"""Shared fixtures for the provider-contract suite (ticket 2).

The suite stubs HTTP at the provider client boundary with
`httpx.MockTransport`. Services are never mocked: each assertion runs the
real client/adapter and records the wire calls it made.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable

import httpx


@dataclass
class RecordedRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes


@dataclass
class FakeTransport:
    """Scripted HTTP transport that records every request.

    Responses are consumed in order. A response may be an `httpx.Response`,
    an exception instance to raise, or a callable taking the request.
    """

    responses: list[Any] = field(default_factory=list)
    requests: list[RecordedRequest] = field(default_factory=list)
    calls: int = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        self.requests.append(
            RecordedRequest(
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers),
                body=request.content,
            )
        )

        if not self.responses:
            return httpx.Response(200, json={})

        item = self.responses.pop(0)
        if callable(item) and not isinstance(item, httpx.Response):
            return item(request)
        if isinstance(item, Exception):
            raise item
        return item

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


@dataclass
class SleepRecorder:
    delays: list[float] = field(default_factory=list)

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class FakeTokens:
    """Token source stand-in; keeps the client's real header logic intact."""

    def __init__(self, token: str = "test-access-token", tenant_id: str | None = None):
        self.token = token
        self.tenant_id = tenant_id

    async def get_access_token(self, **_kwargs) -> str:
        return self.token

    async def get_org_connection(self, **_kwargs):
        return SimpleNamespace(tenant_id=self.tenant_id)


ResponseFactory = Callable[[], list[Any]]


def json_response(status: int, payload: dict | None = None, headers: dict | None = None):
    return httpx.Response(status, json=payload or {}, headers=headers)
