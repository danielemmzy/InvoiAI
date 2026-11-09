from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from app.core.enum.ap import APExceptionStatus, InvoiceAPStatus
from app.core.supabase import get_supabase
from app.repositories.ap.exception_repository import InvoiceExceptionRepository
from app.services.ap.invoice_state_machine import InvoiceStateMachine
from app.services.ap.recovery_service import APRecoveryService
from app.services.audit_service import AuditService
from app.workers.ap_coding_worker import APCodingWorker
from app.workers.ap_matching_worker import APMatchingWorker

logger = logging.getLogger(__name__)


class ExceptionService:
    def __init__(self):
        self.repo = InvoiceExceptionRepository()
        self.db = get_supabase()
        self.state = InvoiceStateMachine(self.db)
        self.audit = AuditService()

    async def list_open(self, org_id):
        return await self.repo.list_open(org_id)

    async def list_for_document(self, org_id, document_id):
        return await self.repo.list_by_document(org_id, document_id)

    async def resolve(self, org_id, exception_id, user_id, note, waive=False):
        note = (note or "").strip()
        existing = self.db.table("invoice_exceptions").select("id,document_id,exception_type,status").eq("org_id", str(org_id)).eq("id", str(exception_id)).limit(1).execute().data or []
        if not existing:
            raise ValueError("Exception not found.")
        exception = existing[0]
        if exception.get("status") in {APExceptionStatus.RESOLVED.value, APExceptionStatus.WAIVED.value}:
            return {"updated": False, "status": exception.get("status"), "document_id": exception["document_id"]}
        if waive and not note:
            raise ValueError("A reason is required when waiving an AP exception.")
        if waive and exception.get("exception_type") == "gl_coding_required":
            raise ValueError("GL coding exceptions cannot be waived. Assign valid GL accounts to every invoice line, then resolve the exception.")

        document_id = UUID(exception["document_id"])
        if exception.get("exception_type") == "gl_coding_required" and not waive:
            # Acknowledge only after the actual line-level issue has been fixed.
            lines = self.db.table("document_line_items").select("id,metadata,gl_account").eq("org_id", str(org_id)).eq("document_id", str(document_id)).execute().data or []
            if not lines:
                raise ValueError("No invoice line items are saved. Open the source invoice, correct the lines, save, then recheck this exception.")
            accounts = self.db.table("chart_of_accounts").select("id,account_code,account_name,is_postable,is_active").eq("org_id", str(org_id)).execute().data or []
            valid_accounts = [a for a in accounts if bool(a.get("is_postable")) and a.get("is_active") is not False]
            missing = []
            for line in lines:
                metadata = line.get("metadata") if isinstance(line.get("metadata"), dict) else {}
                account_id = metadata.get("gl_account_id") or line.get("gl_account_id")
                account_code = metadata.get("gl_account_code") or line.get("gl_account_code") or line.get("gl_account")
                account_name = metadata.get("gl_account_name") or line.get("gl_account_name")
                matched = next((a for a in valid_accounts if (account_id and str(a.get("id")) == str(account_id)) or (account_code and str(a.get("account_code") or "") == str(account_code)) or (account_name and str(a.get("account_name") or "").casefold() == str(account_name).casefold())), None)
                if not matched:
                    missing.append(str(line.get("id") or "line"))
            if missing:
                raise ValueError(f"{len(missing)} invoice line(s) still need a valid, postable GL account. Open the source invoice, assign an account to every line, save the corrections, then click Resolve & recheck.")

        status = APExceptionStatus.WAIVED.value if waive else APExceptionStatus.RESOLVED.value
        self.db.table("invoice_exceptions").update({
            "status": status, "resolved_by": str(user_id), "resolved_at": datetime.now(UTC).isoformat(),
            "resolution_note": note or ("Corrected and marked resolved by reviewer." if not waive else None),
            "updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", str(exception_id)).eq("org_id", str(org_id)).execute()

        try:
            await self.audit.log(
                org_id=org_id,
                user_id=user_id,
                action="ap.exception_waived" if waive else "ap.exception_resolved",
                resource_type="invoice_exception",
                resource_id=exception_id,
                old_values={"status": exception.get("status")},
                new_values={"status": status, "document_id": str(document_id), "exception_type": exception.get("exception_type"), "note": note},
            )
        except Exception:
            # The resolution state is already persisted; don't make the UI report
            # a failed resolution after the mutation. The logging failure remains visible.
            logger.exception("Failed to audit AP exception action for %s", exception_id)
        open_rows = self.db.table("invoice_exceptions").select("id").eq("org_id", str(org_id)).eq("document_id", str(document_id)).in_("status", ["open", "in_review", "escalated"]).execute().data or []
        if open_rows:
            return {"updated": True, "status": status, "document_id": str(document_id), "workflow_resumed": False}

        # A deliberate human retry must not be blocked by an earlier dead-letter
        # marker written by the automatic recovery sweeper.
        await APRecoveryService(self.db).clear(document_id)

        current = await self.state.get_status(document_id)
        if current == InvoiceAPStatus.MATCH_EXCEPTION:
            if waive:
                # An explicit, reasoned override allows the invoice to continue to coding.
                await self.state.transition(document_id, org_id, InvoiceAPStatus.CODING, actor_id=user_id, triggered_by="user", reason="Matching exception waived with documented reason")
                asyncio.create_task(self._retry_coding(document_id), name=f"ap-exception-coding:{document_id}")
            else:
                # Resolution means the underlying data was corrected: re-run deterministic matching.
                await self.state.transition(document_id, org_id, InvoiceAPStatus.VALIDATING, actor_id=user_id, triggered_by="user", reason="Matching exception marked resolved; revalidating invoice")
                asyncio.create_task(self._retry_matching(document_id), name=f"ap-exception-matching:{document_id}")
        elif current == InvoiceAPStatus.CODING_EXCEPTION:
            await self.state.transition(document_id, org_id, InvoiceAPStatus.CODING, actor_id=user_id, triggered_by="user", reason="Coding exception marked resolved; retrying GL coding")
            asyncio.create_task(self._retry_coding(document_id), name=f"ap-exception-coding:{document_id}")

        return {"updated": True, "status": status, "document_id": str(document_id), "workflow_resumed": True}

    async def _retry_matching(self, document_id: UUID):
        try:
            await APMatchingWorker().execute(document_id=document_id)
            refreshed = await self.state.get_status(document_id)
            if refreshed == InvoiceAPStatus.CODING:
                await APCodingWorker().execute(document_id=document_id)
        except Exception:
            logger.exception("AP matching retry after exception resolution failed for %s", document_id)

    async def _retry_coding(self, document_id: UUID):
        try:
            await APCodingWorker().execute(document_id=document_id)
        except Exception as exc:
            logger.exception("AP coding retry after exception resolution failed for %s", document_id)
            rows = self.db.table("documents").select("org_id,ap_status").eq("id", str(document_id)).limit(1).execute().data or []
            if rows:
                org_id = UUID(rows[0]["org_id"])
                current = await self.state.get_status(document_id)
                if current == InvoiceAPStatus.CODING:
                    await self.state.transition(document_id, org_id, InvoiceAPStatus.CODING_EXCEPTION, triggered_by="worker", reason="GL coding retry failed")
                self.db.table("documents").update({
                    "status": "needs_review", "processing_step": "ap_coding_error",
                    "processing_message": "GL coding retry failed. Your saved invoice data was retained. Review the service error and correct missing account assignments before retrying.",
                    "processing_progress": 85, "gl_coding_status": "needs_review", "error_message": str(exc)[:500],
                }).eq("id", str(document_id)).eq("org_id", str(org_id)).execute()
                open_rows = self.db.table("invoice_exceptions").select("id").eq("org_id", str(org_id)).eq("document_id", str(document_id)).eq("exception_type", "gl_coding_required").in_("status", ["open", "in_review", "escalated"]).limit(1).execute().data or []
                if not open_rows:
                    self.db.table("invoice_exceptions").insert({
                        "org_id": str(org_id), "document_id": str(document_id), "exception_type": "gl_coding_required",
                        "severity": "warning", "title": "GL coding retry failed", "details": {"error": str(exc)[:500], "retryable": True},
                    }).execute()
