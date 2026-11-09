"""
============================================================
Vendor Portal Router

Unauthenticated by design — a vendor never gets an InvoiAI
login. Every endpoint here is gated by a single-use, expiring
token (vendor_document_requests.token), not by org/session auth,
and every response is deliberately minimal (no org data, no
other vendor data, no internal identifiers beyond what the
vendor needs to complete their one task).

This router is NOT mounted under /api/v2 (which assumes an
authenticated OrganizationContext) — see main.py.
============================================================
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.vendor.vendor_controls_service import VendorControlsService

router = APIRouter(prefix="/vendor-portal", tags=["Vendor Portal (public, token-gated)"])


class W9Submission(BaseModel):
    document_url: str


class BankVerificationSubmission(BaseModel):
    account_holder_name: str
    bank_name: str
    account_number_last4: str
    routing_number: str


@router.get("/{token}")
async def get_request(token: str):
    try:
        return await VendorControlsService().get_by_token_public(token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{token}/submit-w9")
async def submit_w9(token: str, payload: W9Submission):
    try:
        result = await VendorControlsService().submit_w9(token=token, document_url=payload.document_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": result.status}


@router.post("/{token}/submit-bank-verification")
async def submit_bank_verification(token: str, payload: BankVerificationSubmission):
    """
    Note: only the last 4 digits of the account number are accepted
    here deliberately — full account/routing numbers must go through
    a real banking/KYC provider's hosted, PCI/NACHA-appropriate
    collection flow, not a plain JSON field on this API. This is a
    placeholder shape until that provider integration exists.
    """
    try:
        result = await VendorControlsService().submit_bank_verification(
            token=token, submitted_data=payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": result.status}
