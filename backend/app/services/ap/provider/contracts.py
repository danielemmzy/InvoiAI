"""
Provider contract metadata.

One place to declare what each accounting provider is allowed to expose to
the AP workflow. The provider-contract test suite reads this module so the
same behavioural assertions run against every adapter.

Sage facts come from official Sage documentation and the ADR in
`docs/adr/0001-sage-ap-capability.md`. Sage has no sandbox: its evidence
environment is a **trial business account**, never a sandbox.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.ap.provider.accounting_provider import AccountingProviderError


class UnsupportedProviderOperationError(AccountingProviderError):
    """Raised when a provider cannot perform a requested AP operation."""


@dataclass(frozen=True)
class ProviderContract:
    name: str
    #: Human-readable evidence environment, e.g. "sandbox" or "trial business".
    evidence_environment: str
    #: Header that selects the provider organization. QuickBooks encodes the
    #: realm in the request URL instead of using a header.
    organization_header: str | None
    #: True only when the provider exposes purchase orders to the AP workflow.
    supports_purchase_orders: bool
    #: Resource roots the adapter may call.
    allowed_resources: frozenset[str]
    #: Resource roots the adapter must never call.
    excluded_resources: frozenset[str] = field(default_factory=frozenset)


QUICKBOOKS = ProviderContract(
    name="quickbooks",
    evidence_environment="sandbox",
    organization_header=None,  # realm_id is part of base_url: /v3/company/{realm}
    supports_purchase_orders=True,
    allowed_resources=frozenset(
        {
            "account",
            "bill",
            "companyinfo",
            "customer",
            "invoice",
            "payment",
            "purchaseorder",
            "query",
            "vendor",
        }
    ),
    excluded_resources=frozenset(),
)

XERO = ProviderContract(
    name="xero",
    evidence_environment="sandbox",
    organization_header="Xero-tenant-id",
    supports_purchase_orders=True,
    allowed_resources=frozenset(
        {
            "accounts",
            "contacts",
            "invoices",
            "payments",
            "purchaseorders",
        }
    ),
    excluded_resources=frozenset(),
)

SAGE = ProviderContract(
    name="sage",
    evidence_environment="trial business",
    # Official Sage documentation: `X-Business: <business_id>` selects the
    # business context. Verified from docs, not guessed.
    organization_header="X-Business",
    supports_purchase_orders=False,
    allowed_resources=frozenset(
        {
            "attachments",
            "businesses",
            "contacts",
            "currencies",
            "ledger_accounts",
            "purchase_credit_notes",
            "purchase_invoices",
            "purchase_quick_entries",
            "settings",
            "status_codes",
            "status_types",
            "tax_rates",
            "tax_schemes",
            "user",
        }
    ),
    excluded_resources=frozenset(
        {
            "bank_accounts",
            "bank_transactions",
            "bank_transfers",
            "journals",
            "opening_balances",
            "payment_methods",
            "payments",
            "products",
            "receipts",
            "reports",
            "sales_credit_notes",
            "sales_invoices",
            "sales_quick_entries",
            "services",
        }
    ),
)

PROVIDER_CONTRACTS: dict[str, ProviderContract] = {
    QUICKBOOKS.name: QUICKBOOKS,
    XERO.name: XERO,
    SAGE.name: SAGE,
}


def contract_for(provider: str) -> ProviderContract:
    try:
        return PROVIDER_CONTRACTS[provider.lower()]
    except KeyError as exc:
        raise UnsupportedProviderOperationError(
            f"Unknown accounting provider: {provider}."
        ) from exc


def ensure_purchase_orders_supported(provider: str) -> None:
    """Fail with a typed error instead of calling a provider that has no PO API."""
    contract = contract_for(provider)
    if not contract.supports_purchase_orders:
        raise UnsupportedProviderOperationError(
            f"{contract.name} does not support purchase orders in the InvoiAI AP scope."
        )
