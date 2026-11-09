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
            self.db.table("documents")
            .select("id,ap_status,total_amount,vendor_id,currency")
            .eq("org_id", str(org_id))
            .eq("id", str(document_id))
            .limit(1)
            .execute()
            .data
        )

        if not doc:
            raise ValueError(f"Document {document_id} was not found.")

        doc = doc[0]

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

        vendor = None
        if doc.get("vendor_id"):
            vendor = await self.vendors.get(UUID(doc["vendor_id"]))

        checks["vendor_not_blocked"] = not (vendor and vendor.is_blocked)
        if vendor and vendor.is_blocked:
            reasons.append(f"Vendor is blocked{f': {vendor.blocked_reason}' if vendor.blocked_reason else '.'}")

        checks["w9_on_file"] = not (vendor and vendor.requires_w9 and not vendor.w9_on_file)
        if vendor and vendor.requires_w9 and not vendor.w9_on_file:
            reasons.append("Vendor W-9 is required and not on file.")

        # Support both the legacy verified-bank metadata and the newer
        # provider-tokenized account contract. Never require/store raw account or routing numbers.
        vendor_metadata = getattr(vendor, "metadata", None) or {} if vendor else {}
        bank_verified = bool(
            vendor
            and (
                (getattr(vendor, "bank_provider_account_id", None) and getattr(vendor, "bank_change_verified_at", None))
                or (getattr(vendor, "bank_account_hash", None) and getattr(vendor, "bank_change_verified_at", None))
                or ((vendor_metadata.get("bank_provider_account_id") or vendor_metadata.get("provider_account_id"))
                    and (vendor_metadata.get("payment_verified_at") or vendor_metadata.get("bank_change_verified_at")))
            )
            and not getattr(vendor, "bank_change_pending", False)
        )
        checks["bank_verified"] = bank_verified
        if not bank_verified:
            reasons.append(
                "Vendor payment details have not been verified. Confirm the provider-managed bank account before releasing payment."
            )

        checks["no_payment_hold"] = not (vendor and vendor.payment_hold)
        if vendor and vendor.payment_hold:
            reasons.append(vendor.payment_hold_reason or "Vendor is on a manual payment hold.")

        open_exceptions = await self.exceptions.list_by_document(org_id, document_id)
        open_exceptions = [
            e for e in open_exceptions
            if e.status in (APExceptionStatus.OPEN, APExceptionStatus.IN_REVIEW)
        ]
        checks["exceptions_cleared"] = not open_exceptions
        if open_exceptions:
            reasons.append(f"{len(open_exceptions)} unresolved invoice exception(s).")

        failed_checks = {name for name, passed in checks.items() if not passed}
        hard_blocked = bool(failed_checks & _HARD_BLOCK_CHECKS)

        if hard_blocked:
            status = PaymentAuthorizationStatus.BLOCKED
        elif failed_checks:
            status = PaymentAuthorizationStatus.NEEDS_REVIEW
        else:
            status = PaymentAuthorizationStatus.AUTHORIZED

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
        """

        rows = (
            self.db.table("documents")
            .select("id,vendor_name,total_amount,currency,document_number,due_date,ap_status,erp_bill_id")
            .eq("org_id", str(org_id))
            .eq("ap_status", InvoiceAPStatus.PAYMENT_READY.value)
            .order("due_date")
            .execute()
            .data or []
        )

        queue = []
        for row in rows:
            document_id = UUID(row["id"])
            auth = await self.repository.get_by_document(org_id, document_id)
            if auth is None:
                auth = await self.evaluate(org_id=org_id, document_id=document_id)
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
