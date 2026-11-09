"""
Small, dependency-free observability core.

The MVP does not ship a metrics backend. This registry gives operators a
stable, structured snapshot that a real collector can scrape, while keeping
the metric names bounded so they can be mapped to Prometheus or a hosted
monitor later.

Never record tokens, OTPs, raw document text, provider payloads, or secrets.
Use `redact()` before logging any mapping that came from a request.
"""

from __future__ import annotations

import re
from collections import defaultdict
from threading import Lock
from typing import Any

SENSITIVE_KEYS = {
    "access_token",
    "authorization",
    "client_secret",
    "code",
    "otp",
    "password",
    "refresh_token",
    "secret",
    "token",
}

SENSITIVE_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\b\d{6}\b"),  # six-digit OTPs
)


def redact(value: Any) -> Any:
    """Return a copy with secrets removed, recursively."""
    if isinstance(value, dict):
        return {
            key: ("[redacted]" if str(key).lower() in SENSITIVE_KEYS else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        redacted = value
        for pattern in SENSITIVE_PATTERNS:
            redacted = pattern.sub("[redacted]", redacted)
        return redacted
    return value


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._timings: dict[str, dict[str, float]] = {}
        self._gauges: dict[str, float] = {}

    def increment(self, name: str, value: float = 1.0, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] += value

    def observe(self, name: str, milliseconds: float, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            bucket = self._timings.setdefault(
                key, {"count": 0, "sum": 0.0, "max": 0.0}
            )
            bucket["count"] += 1
            bucket["sum"] += milliseconds
            bucket["max"] = max(bucket["max"], milliseconds)

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            timings = {
                key: {
                    "count": int(bucket["count"]),
                    "avg_ms": round(bucket["sum"] / bucket["count"], 2)
                    if bucket["count"]
                    else 0.0,
                    "max_ms": round(bucket["max"], 2),
                }
                for key, bucket in self._timings.items()
            }
            return {
                "counters": dict(self._counters),
                "timings": timings,
                "gauges": dict(self._gauges),
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._timings.clear()
            self._gauges.clear()

    @staticmethod
    def _key(name: str, labels: dict[str, str]) -> str:
        if not labels:
            return name
        suffix = ",".join(f"{key}={labels[key]}" for key in sorted(labels))
        return f"{name}{{{suffix}}}"


metrics = MetricsRegistry()


# ---------------------------------------------------------------------------
# Named helpers. Keep metric names in one place.
# ---------------------------------------------------------------------------


def record_api_request(*, method: str, route: str, status: int, duration_ms: float) -> None:
    metrics.increment(
        "api_requests_total",
        method=method,
        route=route,
        status_class=f"{status // 100}xx",
    )
    metrics.observe("api_request_duration_ms", duration_ms, route=route)
    if status >= 500:
        metrics.increment("api_errors_total", route=route, status=str(status))


def record_provider_sync(*, provider: str, result: str) -> None:
    metrics.increment("provider_sync_total", provider=provider, result=result)


def record_extraction(*, result: str) -> None:
    metrics.increment("extraction_total", result=result)


def record_webhook(*, provider: str, result: str) -> None:
    metrics.increment("webhook_total", provider=provider, result=result)


def record_notification(*, channel: str, result: str) -> None:
    safe_channel = channel if channel in {"email", "sms", "in_app", "push"} else "other"
    safe_result = result if result in {"success", "failed", "retrying"} else "other"
    metrics.increment(
        "notification_delivery_total", channel=safe_channel, result=safe_result
    )


def record_queue_age(*, queue: str, seconds: float) -> None:
    metrics.set_gauge("queue_age_seconds", seconds, queue=queue)


def record_billing_state(*, plan: str, trial: str, seats: int, allowance: int) -> None:
    metrics.set_gauge("billing_seats", seats, plan=plan)
    metrics.set_gauge("billing_allowance", allowance, plan=plan, trial=trial)


def record_quota_state(*, state: str) -> None:
    metrics.increment("quota_state_total", state=state)
