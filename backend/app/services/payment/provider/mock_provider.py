"""
Mock payment provider.

NOT a real payment rail. Keeps state in memory, always succeeds
instantly (create -> processing -> paid), and exists so the rest
of the payment pipeline (PaymentInstructionService, webhook
handling, reconciliation) can be built and tested end-to-end
before a real provider (Stripe Treasury, Modern Treasury, etc.)
is integrated. Do not use in production.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.services.payment.provider.base import (
    PaymentProvider,
    ProviderPaymentResult,
    ProviderWebhookEvent,
)


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    def __init__(self) -> None:
        # idempotency_key -> provider_payment_id, and provider_payment_id -> status
        self._by_idempotency_key: dict[str, str] = {}
        self._payments: dict[str, dict[str, Any]] = {}

    async def create_payment(
        self,
        *,
        idempotency_key: str,
        amount: Decimal,
        currency: str,
        vendor_id: UUID | None,
        payment_method: str | None,
        metadata: dict[str, Any],
    ) -> ProviderPaymentResult:

        existing_id = self._by_idempotency_key.get(idempotency_key)
        if existing_id:
            record = self._payments[existing_id]
            return ProviderPaymentResult(provider_payment_id=existing_id, status=record["status"], raw=record)

        provider_payment_id = f"mock_{uuid4().hex[:20]}"
        record = {
            "provider_payment_id": provider_payment_id,
            "status": "processing",
            "amount": str(amount),
            "currency": currency,
            "vendor_id": str(vendor_id) if vendor_id else None,
            "payment_method": payment_method,
            "metadata": metadata,
        }
        self._payments[provider_payment_id] = record
        self._by_idempotency_key[idempotency_key] = provider_payment_id
        return ProviderPaymentResult(provider_payment_id=provider_payment_id, status="processing", raw=record)

    async def schedule_payment(self, *, provider_payment_id: str, scheduled_date: str) -> ProviderPaymentResult:
        record = self._require(provider_payment_id)
        record["status"] = "scheduled"
        record["scheduled_date"] = scheduled_date
        return ProviderPaymentResult(provider_payment_id=provider_payment_id, status="scheduled", raw=record)

    async def cancel_payment(self, *, provider_payment_id: str, reason: str) -> ProviderPaymentResult:
        record = self._require(provider_payment_id)
        record["status"] = "cancelled"
        record["cancel_reason"] = reason
        return ProviderPaymentResult(provider_payment_id=provider_payment_id, status="cancelled", raw=record)

    async def get_status(self, *, provider_payment_id: str) -> ProviderPaymentResult:
        record = self._require(provider_payment_id)
        return ProviderPaymentResult(provider_payment_id=provider_payment_id, status=record["status"], raw=record)

    async def handle_webhook(self, *, payload: dict[str, Any], headers: dict[str, str]) -> ProviderWebhookEvent:
        provider_payment_id = payload["provider_payment_id"]
        status = payload.get("status", "paid")
        record = self._payments.setdefault(provider_payment_id, {"provider_payment_id": provider_payment_id})
        record["status"] = status
        return ProviderWebhookEvent(
            provider_payment_id=provider_payment_id,
            status=status,
            occurred_at=payload.get("occurred_at"),
            failure_reason=payload.get("failure_reason"),
            raw=payload,
        )

    async def reconcile(self, *, provider_payment_id: str) -> ProviderPaymentResult:
        return await self.get_status(provider_payment_id=provider_payment_id)

    def _require(self, provider_payment_id: str) -> dict[str, Any]:
        record = self._payments.get(provider_payment_id)
        if record is None:
            raise ValueError(f"Unknown mock payment {provider_payment_id}.")
        return record
