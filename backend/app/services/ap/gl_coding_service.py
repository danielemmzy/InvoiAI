from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Awaitable, Callable
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.enum.ap import APCodingSource, APCodingStatus
from app.models.domain.ap import InvoiceCoding
from app.repositories.ap.chart_of_accounts_repository import ChartOfAccountRepository
from app.repositories.ap.coding_repository import InvoiceCodingRepository, CodingRuleRepository
from app.services.ai.ai_client import create_ai_client

logger = logging.getLogger(__name__)
AUTO_CODE_CONFIDENCE = Decimal("80")
ProgressCallback = Callable[[int, int], Awaitable[None]]


from app.core.db import execute

class GLCodingService:
    def __init__(self, db=None):
        self.coa = ChartOfAccountRepository()
        self.codings = InvoiceCodingRepository()
        self.rules = CodingRuleRepository()
        self.ai = create_ai_client()

    async def code_document(
        self, *, org_id: UUID, document_id: UUID, line_items: list[dict],
        vendor_id: UUID | None = None, on_progress: ProgressCallback | None = None,
    ):
        rules = await self.rules.list_active(org_id)
        accounts = await self.coa.list_by_org(org_id)
        total = len(line_items)
        if not total:
            return []

        # Coding history was previously re-read inside every line's suggestion,
        # costing 1 + 25 + 3*lines queries per document. Load it once instead.
        history = await self._load_history(
            org_id, document_id, vendor_id, line_items
        )

        # Run line suggestions concurrently with a small cap. The old implementation
        # awaited one OpenAI request per line serially, making invoices with many lines
        # appear stuck in GL coding. Rule/history matches remain deterministic.
        semaphore = asyncio.Semaphore(4)
        completed = 0
        progress_lock = asyncio.Lock()

        async def code_one(item):
            nonlocal completed
            async with semaphore:
                coding = await self._code_line(
                    org_id, document_id, item, vendor_id, rules, accounts, history
                )
            async with progress_lock:
                completed += 1
                done = completed
            if on_progress:
                await on_progress(done, total)
            return coding

        codings = await asyncio.gather(*(code_one(item) for item in line_items))
        line_by_id = {str(item.get("id")): item for item in line_items}

        # One aggregated, atomic counter update per document instead of one
        # RPC per matched line.
        matched_rule_ids = [
            coding.coding_rule_id for coding in codings if coding.coding_rule_id
        ]
        if matched_rule_ids:
            await self.rules.increment_match_counts(matched_rule_ids)

        # Codings are persisted in batch (one read, one insert, concurrent
        # updates) rather than two round trips per line.
        await self.codings.save_codings(codings)

        line_updates: list[tuple[str, dict]] = []
        for coding in codings:
            item = line_by_id.get(str(coding.line_item_id), {})
            source_value = getattr(coding.source, "value", coding.source)
            update = {"coding_confidence": float(coding.confidence), "coding_source": str(source_value)}
            if coding.gl_account_id:
                account = next((a for a in accounts if a.id == coding.gl_account_id), None)
                update.update({"gl_account_id": str(coding.gl_account_id), "gl_account_code": account.account_code if account else None, "gl_account_name": account.account_name if account else None})
            if coding.department_id: update["department_id"] = str(coding.department_id)
            if coding.cost_center_id: update["cost_center_id"] = str(coding.cost_center_id)
            if coding.project_id: update["project_id"] = str(coding.project_id)
            if coding.tax_code_id: update["tax_code_id"] = str(coding.tax_code_id)
            if item.get("id"):
                line_updates.append((str(item["id"]), update))
        if line_updates:
            # Each row carries different values, so these stay separate writes;
            # running them concurrently avoids serial network latency.
            await asyncio.gather(*(
                execute(
                    self.codings.db.table("document_line_items")
                    .update(update)
                    .eq("id", item_id)
                    .eq("document_id", str(document_id))
                )
                for item_id, update in line_updates
            ))
        return codings

    async def _load_history(
        self, org_id: UUID, document_id: UUID, vendor_id: UUID | None, line_items: list[dict]
    ) -> dict | None:
        """Load this vendor's recent coding history in a fixed number of queries."""
        descriptions = [str(item.get("description") or "").strip() for item in line_items]
        if not vendor_id or not any(descriptions):
            return None

        docs = (await execute(
            self.codings.db.table("documents")
            .select("id")
            .eq("org_id", str(org_id))
            .eq("vendor_id", str(vendor_id))
            .neq("id", str(document_id))
            .order("created_at", desc=True)
            .limit(25)
        )).data or []
        doc_ids = [str(row["id"]) for row in docs]
        if not doc_ids:
            return None

        items_response, codings_response = await asyncio.gather(
            execute(
                self.codings.db.table("document_line_items")
                .select("id,document_id,description")
                .eq("org_id", str(org_id))
                .in_("document_id", doc_ids)
                .limit(500)
            ),
            execute(
                self.codings.db.table("invoice_codings")
                .select("document_id,line_item_id,gl_account_id")
                .eq("org_id", str(org_id))
                .in_("document_id", doc_ids)
            ),
        )
        items_by_doc: dict[str, list[dict]] = {}
        for row in items_response.data or []:
            items_by_doc.setdefault(str(row.get("document_id")), []).append(row)
        coding_by_item = {
            (str(row.get("document_id")), str(row.get("line_item_id"))): row.get("gl_account_id")
            for row in (codings_response.data or [])
            if row.get("gl_account_id")
        }
        return {
            "doc_ids": doc_ids,
            "items_by_doc": items_by_doc,
            "coding_by_item": coding_by_item,
        }

    async def _code_line(self, org_id, document_id, item, vendor_id, rules, accounts, history=None):
        now = datetime.now(UTC)
        base = dict(id=uuid4(), org_id=org_id, document_id=document_id, line_item_id=item.get("id"), amount=item.get("amount"), created_at=now, updated_at=now)
        # Respect a reviewer-selected account saved on the invoice line. Manual
        # corrections must survive a retry instead of being overwritten by AI.
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        manual_id = item.get("gl_account_id") or metadata.get("gl_account_id")
        manual_code = item.get("gl_account_code") or metadata.get("gl_account_code")
        manual_name = item.get("gl_account_name") or metadata.get("gl_account_name")
        manual_account = next((a for a in accounts if (manual_id and str(a.id) == str(manual_id)) or (manual_code and a.account_code == str(manual_code)) or (manual_name and a.account_name == str(manual_name))), None)
        if manual_account and manual_account.is_postable:
            return InvoiceCoding(**base, gl_account_id=manual_account.id, confidence=Decimal("100"), source=APCodingSource.MANUAL, status=APCodingStatus.APPROVED)
        exact_vendor_rules = [
            rule for rule in rules
            if rule.vendor_id and rule.vendor_id == vendor_id
            and not rule.description_pattern and not rule.sku_pattern
        ]
        pattern_rules = [rule for rule in rules if rule not in exact_vendor_rules]
        for rule in exact_vendor_rules + pattern_rules:
            if self._rule_matches(rule, item, vendor_id):
                # The match counter is incremented once per document, after
                # every line has been coded (see code_document).
                explanation = "Matched the exact supplier coding rule." if rule in exact_vendor_rules else "Matched a description or SKU coding pattern."
                return InvoiceCoding(**base, gl_account_id=rule.gl_account_id, department_id=rule.department_id, cost_center_id=rule.cost_center_id, project_id=rule.project_id, tax_code_id=rule.tax_code_id, confidence=Decimal("95"), source=APCodingSource.RULE, reasoning=explanation, coding_rule_id=rule.id, status=APCodingStatus.AUTO_CODED)

        desc = (item.get("description") or "").strip()
        if vendor_id and desc:
            if history is None:
                # Standalone callers keep the original behaviour; code_document
                # supplies a prefetched history so this path stays batched.
                history = await self._load_history(org_id, document_id, vendor_id, [item])
            if history:
                needle = desc[:80].lower()
                for old_doc_id in history["doc_ids"]:
                    old_items = [
                        row for row in history["items_by_doc"].get(old_doc_id, [])
                        if needle in str(row.get("description") or "").lower()
                    ][:3]
                    for old_item in old_items:
                        account_id = history["coding_by_item"].get((old_doc_id, str(old_item["id"])))
                        if account_id:
                            account = next((a for a in accounts if str(a.id) == str(account_id)), None)
                            if account:
                                return InvoiceCoding(**base, gl_account_id=account.id, confidence=Decimal("90"), source=APCodingSource.HISTORICAL, reasoning="Matched a similar line from this supplier’s coding history.", status=APCodingStatus.AUTO_CODED)

        if accounts and settings.ap_gl_ai_enabled:
            suggestion = await self._ai_suggest(item, accounts)
            if suggestion:
                confidence = Decimal(str(suggestion.get("confidence", 60)))
                account = suggestion.get("account")
                return InvoiceCoding(**base, gl_account_id=account.id if account else None, confidence=confidence, source=APCodingSource.AI_SUGGESTED, reasoning=(suggestion.get("reason") or "Suggested by AI from the invoice line and available accounts.")[:240], status=APCodingStatus.AUTO_CODED if confidence >= AUTO_CODE_CONFIDENCE else APCodingStatus.NEEDS_REVIEW)
        return InvoiceCoding(**base, confidence=Decimal("0"), source=APCodingSource.MANUAL, reasoning="No rule or matching coding history was found; choose an account manually.", status=APCodingStatus.NEEDS_REVIEW)

    @staticmethod
    def _rule_matches(rule, item, vendor_id):
        if rule.vendor_id and rule.vendor_id != vendor_id: return False
        description_match = bool(rule.description_pattern and rule.description_pattern.lower() in (item.get("description") or "").lower())
        sku_match = bool(rule.sku_pattern and rule.sku_pattern.lower() in (item.get("sku") or "").lower())
        if not rule.description_pattern and not rule.sku_pattern:
            return bool(rule.vendor_id and rule.vendor_id == vendor_id)
        return description_match or sku_match

    async def _ai_suggest(self, item, accounts):
        if not settings.ap_gl_ai_enabled or settings.ai_provider == "disabled":
            return None

        choices = [{"id": str(a.id), "code": a.account_code, "name": a.account_name, "type": a.account_type} for a in accounts if a.is_postable]
        if not choices:
            return None

        prompt = (
            "Select the best existing GL account for this invoice line. "
            "Never invent an account. Return JSON: {account_code,confidence,reason}.\n"
            "Line: "
            + json.dumps({k: item.get(k) for k in ("description", "amount", "category", "sku")})
            + "\nAccounts:\n"
            + json.dumps(choices[:200])
        )

        try:
            data = await self.ai.complete_json(
                system_prompt="You are an AP accounting assistant. Select only from the supplied chart of accounts.",
                user_prompt=prompt,
                temperature=0.0,
                timeout=20.0,
            )
            if not data:
                return None
            account = next((a for a in accounts if a.account_code == data.get("account_code")), None)
            return {"account": account, "confidence": data.get("confidence", 60), "reason": data.get("reason")} if account else None
        except Exception:
            logger.exception("GL coding AI suggestion failed")
            return None
