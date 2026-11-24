"""
============================================================
Payment Authorization Service

Answers a different question than the bill-approval workflow:
"Is this already-approved bill authorized to be paid *now*?"

Runs the checks the video calls out explicitly — vendor blocked,
missing W-9/compliance doc, pending bank-account change, manual
payment hold, unresolved matching/coding exceptions — and blocks
payment release when any of them fail. A privileged user
(permission-gated at the router) can override a block, which is
recorded with who/when/why for the audit trail.

This intentionally does not decide *when* to run — callers
(BillSyncWorker, or a manual re-check endpoint) call evaluate()
whenever they want the authorization recomputed.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.core.enum.ap import APExceptionStatus, InvoiceAPStatus, PaymentAuthorizationStatus
from app.core.supabase import get_supabase
from app.models.domain.ap import PaymentAuthorization
from app.repositories.ap.exception_repository import InvoiceExceptionRepository
from app.repositories.ap.payment_authorization_repository import PaymentAuthorizationRepository
from app.repositories.document.vendor_repository import VendorRepository

# Any of these fail the payment outright, regardless of everything else.
_HARD_BLOCK_CHECKS = {"bill_approved", "vendor_not_blocked", "w9_on_file", "bank_verified", "no_payment_hold"}


from app.core.db import execute


def _read(record, key, default=None):
    """Read a field from either a domain model or a raw database row."""
    if record is None:
        return default
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def _status_value(status):
    return getattr(status, "value", status)


class PaymentAuthorizationService:

    def __init__(
        self,
        db=None,
        repository: PaymentAuthorizationRepository | None = None,
        vendors: VendorRepository | None = None,
        exceptions: InvoiceExceptionRepository | None = None,
    ) -> None:
        self.db = db or get_supabase()
        self.repository = repository or PaymentAuthorizationRepository()
        self.vendors = vendors or VendorRepository()
        self.exceptions = exceptions or InvoiceExceptionRepository()

    # =========================================================
    # Evaluate
    # =========================================================

    async def evaluate(self, *, org_id: UUID, document_id: UUID) -> PaymentAuthorization:

        doc = (
            (await execute(self.db.table("documents")
            .select("id,ap_status,total_amount,vendor_id,currency")
            .eq("org_id", str(org_id))
            .eq("id", str(document_id))
            .limit(1)))
            .data
        )

        if not doc:
            raise ValueError(f"Document {document_id} was not found.")

        doc = doc[0]

        vendor = None
        if doc.get("vendor_id"):
            vendor = await self.vendors.get(UUID(doc["vendor_id"]))

        open_exceptions = await self.exceptions.list_by_document(org_id, document_id)
        exception_statuses = [
            _status_value(_read(exception, "status"))
            for exception in open_exceptions
            if _status_value(_read(exception, "status"))
            in (APExceptionStatus.OPEN.value, APExceptionStatus.IN_REVIEW.value)
        ]

        status, reasons, checks = self._evaluate_checks(doc, vendor, exception_statuses)

        payload = {
            "status": status.value,
            "blocked_reasons": reasons,
            "checks": checks,
        }
        if status == PaymentAuthorizationStatus.AUTHORIZED:
            payload["authorized_at"] = datetime.now(UTC).isoformat()

        updated = await self.repository.upsert(org_id, document_id, payload)
        if updated is None:
            raise RuntimeError(f"Failed to record payment authorization for {document_id}.")
        return updated

    @staticmethod
    def _evaluate_checks(doc, vendor, exception_statuses: list[str]):
        """Compute the authorization decision from already-loaded data.

        Shared by the single-document ``evaluate`` and the batched queue so both
        paths apply exactly the same rules.
        """

        checks: dict[str, bool] = {}
        reasons: list[str] = []

        bill_approved = doc.get("ap_status") in {
            InvoiceAPStatus.APPROVED.value,
            InvoiceAPStatus.SYNCING_TO_ERP.value,
            InvoiceAPStatus.PAYMENT_READY.value,
            InvoiceAPStatus.PAID.value,
            InvoiceAPStatus.RECONCILED.value,
        }
        checks["bill_approved"] = bill_approved
        if not bill_approved:
            reasons.append("Bill has not completed approval.")

        vendor_blocked = bool(_read(vendor, "is_blocked"))
        checks["vendor_not_blocked"] = not vendor_blocked
        if vendor_blocked:
            blocked_reason = _read(vendor, "blocked_reason")
            reasons.append(
                f"Vendor is blocked{f': {blocked_reason}' if blocked_reason else '.'}"
            )

        requires_w9 = bool(_read(vendor, "requires_w9"))
        w9_on_file = bool(_read(vendor, "w9_on_file"))
        checks["w9_on_file"] = not (vendor is not None and requires_w9 and not w9_on_file)
        if vendor is not None and requires_w9 and not w9_on_file:
            reasons.append("Vendor W-9 is required and not on file.")

        # Support both the legacy verified-bank metadata and the newer
        # provider-tokenized account contract. Never require/store raw account or routing numbers.
        vendor_metadata = _read(vendor, "metadata") or {}
        verified_at = _read(vendor, "bank_change_verified_at")
        bank_verified = bool(
            vendor is not None
            and (
                (_read(vendor, "bank_provider_account_id") and verified_at)
                or (_read(vendor, "bank_account_hash") and verified_at)
                or (
                    (vendor_metadata.get("bank_provider_account_id") or vendor_metadata.get("provider_account_id"))
                    and (vendor_metadata.get("payment_verified_at") or vendor_metadata.get("bank_change_verified_at"))
                )
            )
            and not _read(vendor, "bank_change_pending")
        )
        checks["bank_verified"] = bank_verified
        if not bank_verified:
            reasons.append(
                "Vendor payment details have not been verified. Confirm the provider-managed bank account before releasing payment."
            )

        payment_hold = bool(_read(vendor, "payment_hold"))
        checks["no_payment_hold"] = not payment_hold
        if payment_hold:
            reasons.append(
                _read(vendor, "payment_hold_reason") or "Vendor is on a manual payment hold."
            )

        checks["exceptions_cleared"] = not exception_statuses
        if exception_statuses:
            reasons.append(
                f"{len(exception_statuses)} unresolved invoice exception(s)."
            )

        failed_checks = {name for name, passed in checks.items() if not passed}
        hard_blocked = bool(failed_checks & _HARD_BLOCK_CHECKS)

        if hard_blocked:
            status = PaymentAuthorizationStatus.BLOCKED
        elif failed_checks:
            status = PaymentAuthorizationStatus.NEEDS_REVIEW
        else:
            status = PaymentAuthorizationStatus.AUTHORIZED

        return status, reasons, checks

    # =========================================================
    # Override
    # =========================================================

    async def override(
        self,
        *,
        org_id: UUID,
        document_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> PaymentAuthorization:

        if not reason or not reason.strip():
            raise ValueError("An override reason is required.")

        existing = await self.repository.get_by_document(org_id, document_id)
        if existing is None:
            existing = await self.evaluate(org_id=org_id, document_id=document_id)

        if existing.status == PaymentAuthorizationStatus.AUTHORIZED:
            raise ValueError("This payment is already authorized; no override needed.")

        now = datetime.now(UTC).isoformat()

        updated = await self.repository.upsert(
            org_id,
            document_id,
            {
                "status": PaymentAuthorizationStatus.AUTHORIZED.value,
                "override_by": str(actor_id),
                "override_at": now,
                "override_reason": reason.strip(),
                "authorized_by": str(actor_id),
                "authorized_at": now,
            },
        )

        if updated is None:
            raise RuntimeError(f"Failed to override payment authorization for {document_id}.")

        return updated

    # =========================================================
    # Queue
    # =========================================================

    async def list_queue(self, org_id: UUID) -> list[dict]:
        """
        Documents that have cleared bill approval and are waiting on
        payment release, each annotated with its current authorization
        status (evaluated lazily if it hasn't been computed yet).

        The queue used to run ``get_by_document`` per row and, for rows with no
        stored authorization, a full ``evaluate`` (several more queries). Both
        are now batched: authorizations are read once, and any missing decisions
        are computed from one vendor query and one exception query.
        """

        rows = (
            (await execute(self.db.table("documents")
            .select("id,vendor_id,vendor_name,total_amount,currency,document_number,due_date,ap_status,erp_bill_id")
            .eq("org_id", str(org_id))
            .eq("ap_status", InvoiceAPStatus.PAYMENT_READY.value)
            .order("due_date")))
            .data or []
        )

        if not rows:
            return []

        document_ids = [str(row["id"]) for row in rows]
        authorizations = await self.repository.list_by_documents(org_id, document_ids)
        auth_by_document = {
            str(auth.document_id): auth for auth in authorizations
        }

        missing = [
            row for row in rows
            if str(row["id"]) not in auth_by_document
        ]
        if missing:
            vendor_ids = sorted({
                str(row.get("vendor_id")) for row in missing if row.get("vendor_id")
            })
            vendor_rows = []
            if vendor_ids:
                vendor_rows = (
                    (await execute(self.db.table("vendors")
                    .select("*")
                    .eq("org_id", str(org_id))
                    .in_("id", vendor_ids)))
                    .data or []
                )
            vendors_by_id = {str(vendor["id"]): vendor for vendor in vendor_rows}

            missing_ids = [str(row["id"]) for row in missing]
            exception_rows = (
                (await execute(self.db.table("invoice_exceptions")
                .select("document_id,status")
                .eq("org_id", str(org_id))
                .in_("document_id", missing_ids)
                .in_("status", [
                    APExceptionStatus.OPEN.value,
                    APExceptionStatus.IN_REVIEW.value,
                ])))
                .data or []
            )
            exceptions_by_document: dict[str, list[str]] = {}
            for exception in exception_rows:
                exceptions_by_document.setdefault(
                    str(exception.get("document_id")), []
                ).append(str(exception.get("status")))

            now = datetime.now(UTC).isoformat()
            pending: list[tuple[str, dict]] = []
            for row in missing:
                document_id = str(row["id"])
                status, reasons, checks = self._evaluate_checks(
                    row,
                    vendors_by_id.get(str(row.get("vendor_id") or "")),
                    exceptions_by_document.get(document_id, []),
                )
                payload = {
                    "status": status.value,
                    "blocked_reasons": reasons,
                    "checks": checks,
                }
                if status == PaymentAuthorizationStatus.AUTHORIZED:
                    payload["authorized_at"] = now
                pending.append((document_id, payload))

            saved = await self.repository.upsert_many(org_id, pending)
            for authorization in saved:
                auth_by_document[str(authorization.document_id)] = authorization
            decision_by_document = {
                document_id: payload for document_id, payload in pending
            }
        else:
            decision_by_document = {}

        queue = []
        for row in rows:
            auth = auth_by_document.get(str(row["id"]))
            if auth is None:
                # The bulk upsert did not return this row (for example a
                # concurrent delete). The decision for it was already computed
                # in this pass from the same document, vendor and exception
                # data, so reuse it instead of re-running evaluate() per row.
                decision = decision_by_document.get(str(row["id"]))
                if decision is not None:
                    queue.append(
                        {
                            "document_id": row["id"],
                            "vendor_name": row.get("vendor_name"),
                            "amount": row.get("total_amount"),
                            "currency": row.get("currency"),
                            "document_number": row.get("document_number"),
                            "due_date": row.get("due_date"),
                            "erp_bill_id": row.get("erp_bill_id"),
                            "authorization_status": decision["status"],
                            "blocked_reasons": decision["blocked_reasons"],
                        }
                    )
                    continue
                auth = await self.evaluate(org_id=org_id, document_id=UUID(row["id"]))
            queue.append(
                {
                    "document_id": row["id"],
                    "vendor_name": row.get("vendor_name"),
                    "amount": row.get("total_amount"),
                    "currency": row.get("currency"),
                    "document_number": row.get("document_number"),
                    "due_date": row.get("due_date"),
                    "erp_bill_id": row.get("erp_bill_id"),
                    "authorization_status": auth.status,
                    "blocked_reasons": auth.blocked_reasons,
                }
            )
        return queue
