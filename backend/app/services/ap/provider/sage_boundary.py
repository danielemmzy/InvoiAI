"""
Sage AP resource boundary.

The agreed Sage scope is deliberately narrow. This guard is the single place
that decides which Sage Accounting API resources an adapter may touch, so a
future adapter cannot silently call an excluded resource (banking, payments,
journals, sales, opening balances, products/services, or reporting).

Usage in the Sage adapter:

    assert_sage_allowed("POST", "/purchase_invoices")
    assert_sage_allowed("GET", "/bank_accounts")  # raises
"""

from __future__ import annotations

from app.services.ap.provider.accounting_provider import AccountingProviderError
from app.services.ap.provider.contracts import SAGE

READ_METHODS = frozenset({"GET", "HEAD"})
WRITE_ALLOWED_RESOURCES = frozenset(
    {
        "purchase_credit_notes",
        "purchase_invoices",
        "purchase_quick_entries",
    }
)


class SageUnsupportedResourceError(AccountingProviderError):
    """A Sage operation falls outside the agreed AP resource scope."""


def _resource_root(path: str) -> str:
    clean = path.split("?", 1)[0].strip("/")
    return clean.split("/", 1)[0].lower() if clean else ""


def assert_sage_allowed(method: str, path: str) -> None:
    root = _resource_root(path)
    if not root:
        raise SageUnsupportedResourceError("Sage request path is empty.")

    if root in SAGE.excluded_resources:
        raise SageUnsupportedResourceError(
            f"Sage resource '{root}' is excluded from the InvoiAI AP scope."
        )

    if root not in SAGE.allowed_resources:
        raise SageUnsupportedResourceError(
            f"Sage resource '{root}' is not in the approved AP resource list."
        )

    upper = method.upper()
    if upper not in READ_METHODS and root not in WRITE_ALLOWED_RESOURCES:
        raise SageUnsupportedResourceError(
            f"Sage resource '{root}' is read-only in the InvoiAI AP scope."
        )

    if upper == "DELETE":
        raise SageUnsupportedResourceError(
            "Sage deletes are not part of the InvoiAI AP scope."
        )
