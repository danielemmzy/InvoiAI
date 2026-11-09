"""
============================================================
Payment Provider Abstraction

The AP system must stay provider-independent (spec P0/P2):
no ACH/wire/check infrastructure is implemented here. This
defines the contract every real provider (Stripe Treasury,
Modern Treasury, Dwolla, etc.) would implement, plus a
MockPaymentProvider used for local development and tests.

PaymentInstructionService (payment_instruction_service.py) is
the only caller — AP business logic never talks to a provider
directly, and never hardcodes a provider name into a decision.
============================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass
class ProviderPaymentResult:
    provider_payment_id: str
    status: str  # provider-native status string; the caller maps this to PaymentInstructionStatus
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderWebhookEvent:
    provider_payment_id: str
    status: str
    occurred_at: str | None = None
    failure_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentProvider(ABC):
    """
    One implementation per payment rail/vendor. All methods are
    async and idempotent: calling create_payment() twice with the
    same idempotency_key must not create two payments.
    """

    name: str = "abstract"

    @abstractmethod
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
        """Create (but not necessarily execute) a payment with the provider."""
        raise NotImplementedError

    @abstractmethod
    async def schedule_payment(
        self,
        *,
        provider_payment_id: str,
        scheduled_date: str,
    ) -> ProviderPaymentResult:
        """Schedule an already-created payment for a future date."""
        raise NotImplementedError

    @abstractmethod
    async def cancel_payment(self, *, provider_payment_id: str, reason: str) -> ProviderPaymentResult:
        raise NotImplementedError

    @abstractmethod
    async def get_status(self, *, provider_payment_id: str) -> ProviderPaymentResult:
        raise NotImplementedError

    @abstractmethod
    async def handle_webhook(self, *, payload: dict[str, Any], headers: dict[str, str]) -> ProviderWebhookEvent:
        """Verify + parse an inbound provider webhook into a normalized event."""
        raise NotImplementedError

    @abstractmethod
    async def reconcile(self, *, provider_payment_id: str) -> ProviderPaymentResult:
        """Re-fetch a payment's authoritative status directly from the provider (not from a cached webhook)."""
        raise NotImplementedError
