"""Ticket 6 — metrics, redaction, and alert delivery."""

from __future__ import annotations

import httpx
import pytest

from app.core.config import settings
from app.core.observability import (
    MetricsRegistry,
    metrics,
    record_provider_sync,
    record_notification,
    redact,
)
from app.services.observability.alerts import ALERT_RUNBOOKS, Alert, AlertService


@pytest.fixture(autouse=True)
def _reset_metrics():
    metrics.reset()
    yield
    metrics.reset()


def test_redaction_removes_secrets_and_otps_recursively():
    payload = {
        "access_token": "secret-token",
        "nested": {"refresh_token": "refresh", "amount": 10},
        "header": "Authorization: Bearer abc.def.ghi",
        "otp": "123456",
        "message": "Your code is 654321",
        "list": ["Bearer zzz.yyy.xxx", {"password": "hunter2"}],
    }

    cleaned = redact(payload)

    assert cleaned["access_token"] == "[redacted]"
    assert cleaned["nested"]["refresh_token"] == "[redacted]"
    assert cleaned["nested"]["amount"] == 10
    assert "Bearer" not in cleaned["header"]
    assert cleaned["otp"] == "[redacted]"
    assert "654321" not in cleaned["message"]
    assert "zzz.yyy.xxx" not in cleaned["list"][0]
    assert cleaned["list"][1]["password"] == "[redacted]"


def test_metrics_registry_accumulates_and_summarises():
    registry = MetricsRegistry()
    registry.increment("requests", method="GET")
    registry.increment("requests", method="GET")
    registry.increment("requests", method="POST")
    registry.observe("latency", 10, route="/a")
    registry.observe("latency", 30, route="/a")
    registry.set_gauge("queue_age_seconds", 42, queue="ocr")

    snapshot = registry.snapshot()

    assert snapshot["counters"]["requests{method=GET}"] == 2
    assert snapshot["counters"]["requests{method=POST}"] == 1
    assert snapshot["timings"]["latency{route=/a}"] == {
        "count": 2,
        "avg_ms": 20.0,
        "max_ms": 30.0,
    }
    assert snapshot["gauges"]["queue_age_seconds{queue=ocr}"] == 42


def test_provider_sync_metric_has_a_stable_name():
    record_provider_sync(provider="quickbooks", result="success")
    snapshot = metrics.snapshot()
    assert snapshot["counters"]["provider_sync_total{provider=quickbooks,result=success}"] == 1


def test_notification_metric_does_not_use_unbounded_channel_labels():
    record_notification(channel="customer@example.test", result="failed")
    assert "notification_delivery_total{channel=other,result=failed}" in metrics.snapshot()["counters"]


async def test_alert_delivery_requires_a_configured_webhook(monkeypatch):
    monkeypatch.setattr(settings, "alert_webhook_url", "")

    result = await AlertService().send(
        Alert(
            name="worker_stuck",
            severity="critical",
            summary="OCR queue age above 15 minutes",
            runbook=ALERT_RUNBOOKS["worker_stuck"],
        )
    )

    assert result["delivered"] is False
    assert result["reason"] == "alert_webhook_not_configured"
    assert result["alert"]["runbook"].endswith("#stuck-workers")


async def test_test_alert_is_delivered_end_to_end(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(202, json={"ok": True})

    monkeypatch.setattr(settings, "alert_webhook_url", "https://alerts.example.test/hook")

    result = await AlertService(transport=httpx.MockTransport(handler)).send(
        Alert(
            name="test_alert",
            severity="info",
            summary="End-to-end alert delivery test.",
            runbook=ALERT_RUNBOOKS["worker_stuck"],
        )
    )

    assert result["delivered"] is True
    assert result["status_code"] == 202
    assert len(calls) == 1
    body = calls[0].content.decode()
    assert "test_alert" in body
    assert "alert_webhook_url" not in body


async def test_alert_payload_never_contains_customer_secrets(monkeypatch):
    monkeypatch.setattr(settings, "alert_webhook_url", "https://alerts.example.test/hook")
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        return httpx.Response(200)

    alert = Alert(
        name="provider_outage",
        severity="critical",
        summary="Provider rejected token Bearer supersecret and OTP 123456",
        runbook=ALERT_RUNBOOKS["provider_outage"],
    )

    await AlertService(transport=httpx.MockTransport(handler)).send(alert)

    assert "supersecret" not in captured["body"]
    assert "123456" not in captured["body"]
