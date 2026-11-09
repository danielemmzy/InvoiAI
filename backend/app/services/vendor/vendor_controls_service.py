"""
============================================================
Vendor Controls Service

W-9 workflow:
  missing W9 -> request (token link) -> vendor submits document
  -> vendor.w9_on_file=True, vendor.w9_document_url set
  -> payment block clears once every other control also passes
  (PaymentAuthorizationService re-evaluates independently; this
  service does not decide payment authorization).

Bank-change workflow (more sensitive — never silently applied):
  vendor requests/reports a bank change -> vendor.bank_change_pending=True
  (this alone is enough to BLOCK payment per PaymentAuthorizationService)
  -> internal user explicitly verifies (approve/reject)
  -> approve: pending clears, bank_change_verified_at set,
     new account details applied to vendor.metadata (opaque —
     account/routing numbers are never stored as first-class
     columns; see <never_store>-equivalent handling upstream)
  -> reject: pending stays cleared but no details are applied,
     rejection_reason recorded.

A pending bank change is NEVER auto-approved by document
submission alone — verify_bank_change() always requires an
explicit actor + decision.
============================================================
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.ap import VendorDocumentRequestStatus, VendorDocumentRequestType
from app.repositories.ap.vendor_document_request_repository import VendorDocumentRequestRepository
from app.repositories.document.vendor_repository import VendorRepository


class VendorControlsService:

    def __init__(
        self,
        requests: VendorDocumentRequestRepository | None = None,
        vendors: VendorRepository | None = None,
    ) -> None:
        self.requests = requests or VendorDocumentRequestRepository()
        self.vendors = vendors or VendorRepository()

    # =========================================================
    # Request (internal, authenticated)
    # =========================================================

    async def request_document(
        self, *, org_id: UUID, vendor_id: UUID, request_type: VendorDocumentRequestType, requested_by: UUID,
    ):
        vendor = await self.vendors.get(vendor_id)
        if vendor is None or str(vendor.org_id) != str(org_id):
            raise ValueError("Vendor not found.")

        token = secrets.token_urlsafe(32)
        created = await self.requests.create_request({
            "org_id": str(org_id),
            "vendor_id": str(vendor_id),
            "request_type": request_type.value,
            "status": VendorDocumentRequestStatus.PENDING.value,
            "token": token,
        })
        if created is None:
            raise RuntimeError("Failed to create vendor document request.")

        if request_type == VendorDocumentRequestType.W9:
            await self.vendors.update(vendor_id, {"requires_w9": True})

        return created

    async def list_for_vendor(self, org_id: UUID, vendor_id: UUID):
        return await self.requests.list_for_vendor(org_id, vendor_id)

    # =========================================================
    # Submit (public, token-authenticated — no vendor login)
    # =========================================================

    async def get_by_token_public(self, token: str) -> dict:
        """
        Returns only what an unauthenticated vendor-facing page needs
        to render — never the full request/vendor row.
        """
        request = await self.requests.get_by_token(token)
        if request is None:
            raise ValueError("This link is invalid.")
        if request.status != VendorDocumentRequestStatus.PENDING:
            raise ValueError("This request has already been completed or is no longer active.")
        if request.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            await self.requests.update_status(request.id, {"status": VendorDocumentRequestStatus.EXPIRED.value})
            raise ValueError("This link has expired — ask your AP contact to send a new one.")

        vendor = await self.vendors.get(request.vendor_id)
        return {
            "request_type": request.request_type,
            "vendor_name": vendor.name if vendor else None,
        }

    async def submit_w9(self, *, token: str, document_url: str):
        request = await self._require_pending(token, VendorDocumentRequestType.W9)

        updated_request = await self.requests.update_status(request.id, {
            "status": VendorDocumentRequestStatus.SUBMITTED.value,
            "submitted_at": datetime.now(UTC).isoformat(),
            "document_url": document_url,
        })

        await self.vendors.update(request.vendor_id, {"w9_on_file": True, "w9_document_url": document_url})
        return updated_request

    async def submit_bank_verification(self, *, token: str, submitted_data: dict):
        """
        Records the vendor's submitted new banking details as PENDING —
        this does NOT apply them and does NOT clear the payment block.
        An internal user must call verify_bank_change() explicitly.
        """
        request = await self._require_pending(token, VendorDocumentRequestType.BANK_VERIFICATION)

        updated_request = await self.requests.update_status(request.id, {
            "status": VendorDocumentRequestStatus.SUBMITTED.value,
            "submitted_at": datetime.now(UTC).isoformat(),
            "submitted_data": submitted_data,
        })

        await self.vendors.update(request.vendor_id, {
            "bank_change_pending": True,
            "bank_change_requested_at": datetime.now(UTC).isoformat(),
        })
        return updated_request

    async def _require_pending(self, token: str, expected_type: VendorDocumentRequestType):
        request = await self.requests.get_by_token(token)
        if request is None:
            raise ValueError("This link is invalid.")
        if request.request_type != expected_type:
            raise ValueError("This link is for a different request type.")
        if request.status != VendorDocumentRequestStatus.PENDING:
            raise ValueError("This request has already been completed or is no longer active.")
        return request

    # =========================================================
    # Verify (internal, authenticated — bank changes only; W-9 has
    # no separate verify step, it clears the block on submission)
    # =========================================================

    async def verify_bank_change(self, *, org_id: UUID, request_id: UUID, actor_id: UUID, approve: bool, reason: str | None = None):
        request = await self.requests.get(request_id)
        if request is None or str(request.org_id) != str(org_id):
            raise ValueError("Vendor document request not found.")
        if request.request_type != VendorDocumentRequestType.BANK_VERIFICATION:
            raise ValueError("This request is not a bank-change verification.")
        if request.status != VendorDocumentRequestStatus.SUBMITTED:
            raise ValueError("Only a submitted bank-change request can be verified.")

        now = datetime.now(UTC).isoformat()

        if approve:
            updated_request = await self.requests.update_status(request_id, {
                "status": VendorDocumentRequestStatus.VERIFIED.value,
                "verified_by": str(actor_id), "verified_at": now,
            })
            vendor = await self.vendors.get(request.vendor_id)
            # WARNING: submitted_data is stored as-is in vendor.metadata
            # for this build. Before production use, replace this with
            # a tokenized reference from a real banking/KYC provider —
            # raw account/routing numbers must never be persisted in
            # plaintext application storage.
            merged_metadata = {**(vendor.metadata if vendor else {}), "bank_details": request.submitted_data}
            await self.vendors.update(request.vendor_id, {
                "bank_change_pending": False,
                "bank_change_verified_at": now,
                "bank_account_changed_at": now,
                "metadata": merged_metadata,
            })
        else:
            if not reason or not reason.strip():
                raise ValueError("A rejection reason is required.")
            updated_request = await self.requests.update_status(request_id, {
                "status": VendorDocumentRequestStatus.REJECTED.value,
                "verified_by": str(actor_id), "verified_at": now, "rejection_reason": reason.strip(),
            })
            # Payment stays blocked (bank_change_pending remains True) —
            # a rejected submission is not the same as "no pending
            # change"; an AP admin must follow up with the vendor.

        return updated_request
