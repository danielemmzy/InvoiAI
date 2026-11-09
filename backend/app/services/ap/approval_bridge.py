from __future__ import annotations
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from app.core.enum.application import ApprovalStatus
from app.core.enum.ap import ApprovalRuleScope, InvoiceAPStatus
from app.services.ap.invoice_state_machine import InvoiceStateMachine
from app.core.enum.database import ApprovalDecision, RiskLevel
from app.core.supabase import get_supabase
from app.models.domain.approval import ApprovalStep, ApprovalWorkflow
from app.repositories.approval.history_repository import ApprovalHistoryRepository
from app.repositories.approval.step_repository import ApprovalStepRepository
from app.repositories.approval.workflow_repository import ApprovalWorkflowRepository
from app.services.approval.approval_engine import ApprovalEngine
from app.services.audit_service import AuditService
from app.repositories.audit.audit_repository import AuditRepository
from app.services.ap.routing_engine import APRoutingEngine
from app.workers.bill_sync_worker import BillSyncWorker


def document_routing_dimensions(
    doc: dict,
) -> tuple[str | None, str | None, str | None]:
    """Read department/cost-center/location without assuming dedicated columns.

    ``documents`` stores intake dimensions in its JSON payloads, not in
    ``department``/``cost_center``/``location`` columns. Capture overrides are
    the most specific source, so they win over the original external payload.
    """
    values: dict[str, str] = {}
    for source in (doc.get("capture_overrides"), doc.get("external_source_data")):
        if not isinstance(source, dict):
            continue
        for key in ("department", "cost_center", "location"):
            value = source.get(key)
            if isinstance(value, str):
                value = value.strip()
            if key not in values and value not in (None, ""):
                values[key] = str(value)
    return values.get("department"), values.get("cost_center"), values.get("location")


class APApprovalBridge:
    """
    Bridges an AP-automated document into the canonical approval
    engine (app/services/approval/approval_engine.py).

    This class does exactly two things:

    1. Gathers AP-specific context (document/vendor amount, risk,
       PO requirement) and asks APRoutingEngine for an ApprovalPlan
       (who approves, in what stages, under which execution mode).
       It then hands that plan to ApprovalEngine.start_workflow(),
       which is the single place that persists and validates
       approval workflows/steps. This class never inserts into
       approval_workflows/approval_steps directly.

    2. Reacts to a decision ApprovalEngine already processed (via
       POST /approvals/{step_id}/decide -> ApprovalEngine.process_decision)
       by applying the AP-specific side effects: syncing the
       document's ap_status and kicking off ERP sync on approval,
       marking it rejected on rejection. It does not re-derive
       workflow completion itself — ApprovalEngine.process_decision
       is the sole authority on workflow status.
    """

    def __init__(self, db=None, routing_engine: APRoutingEngine | None = None):
        self.db = db or get_supabase()
        self.routing_engine = routing_engine or APRoutingEngine(self.db)
        self.engine = ApprovalEngine(
            ApprovalWorkflowRepository(),
            ApprovalStepRepository(),
            ApprovalHistoryRepository(),
            audit_service=AuditService(repository=AuditRepository()),
        )

    async def create_workflow(self, *, org_id: UUID, document_id: UUID, analysis_id: UUID, initiated_by: UUID | None):
        # Idempotency: never create a second workflow for the same document.
        existing = (
            self.db.table("approval_workflows")
            .select("id")
            .eq("org_id", str(org_id))
            .eq("document_id", str(document_id))
            .limit(1)
            .execute()
        )
        if existing.data:
            workflow_id = existing.data[0]["id"]
            has_step = (
                self.db.table("approval_steps")
                .select("id")
                .eq("workflow_id", str(workflow_id))
                .limit(1)
                .execute()
                .data
            )
            if has_step:
                return workflow_id

            # A workflow with no steps is an interrupted creation (the
            # workflow row is inserted before its steps). Remove the partial
            # record so this submission can create a complete workflow.
            self.db.table("approval_workflows").delete().eq(
                "id", str(workflow_id)
            ).execute()

        doc = self.db.table("documents").select(
            "total_amount,document_type,vendor_name,vendor_id,external_source_data,capture_overrides"
        ).eq("org_id", str(org_id)).eq("id", str(document_id)).single().execute().data
        analysis = self.db.table("document_analyses").select("risk_level").eq("org_id", str(org_id)).eq("id", str(analysis_id)).single().execute().data

        amount = Decimal(str(doc.get("total_amount") or 0))
        risk_level = analysis.get("risk_level") or RiskLevel.MEDIUM.value
        department, cost_center, location = document_routing_dimensions(doc)

        vendor_id = UUID(doc["vendor_id"]) if doc.get("vendor_id") else None
        requires_po = None
        extra_context: dict = {}
        if vendor_id:
            vendor_row = self.db.table("vendors").select("po_required,is_verified,is_blocked").eq("org_id", str(org_id)).eq("id", str(vendor_id)).limit(1).execute().data
            if vendor_row:
                requires_po = bool(vendor_row[0]["po_required"])
                extra_context["vendor_verified"] = bool(vendor_row[0].get("is_verified"))
                extra_context["vendor_blocked"] = bool(vendor_row[0].get("is_blocked"))

        open_exceptions = self.db.table("invoice_exceptions").select("id").eq("org_id", str(org_id)).eq("document_id", str(document_id)).eq("status", "open").execute().data
        extra_context["exception_status"] = "open" if open_exceptions else "none"

        plan, execution_mode, auto_decision = await self.routing_engine.build_plan(
            org_id=org_id,
            amount=amount,
            vendor_id=vendor_id,
            department=department,
            cost_center=cost_center,
            location=location,
            document_type=doc.get("document_type"),
            risk_level=risk_level,
            requires_po=requires_po,
            scope=ApprovalRuleScope.BILL,
            extra_context=extra_context,
        )

        if auto_decision is not None:
            return await self._apply_auto_decision(
                org_id=org_id, document_id=document_id, auto_decision=auto_decision,
            )

        if not plan:
            raise ValueError("No active approver is configured for this organization.")

        fallback_initiator = next((step.approver_id for step in plan if step.approver_id), None)
        initiator = initiated_by or fallback_initiator
        if initiator is None:
            raise ValueError("Unable to determine an initiator for this approval workflow — the first step has no resolvable approver.")

        now = datetime.now(UTC)
        due = now + timedelta(days=2)
        workflow_id = uuid4()

        # parallel/any_one: every planned step activates together as one
        # stage. sequential/group: each step is its own stage, activated
        # in order (group additionally requires a claim before it can be
        # decided — see ApprovalGroupService.claim_step).
        single_stage = execution_mode in ("parallel", "any_one")

        workflow = ApprovalWorkflow(
            id=workflow_id,
            org_id=org_id,
            document_id=document_id,
            analysis_id=analysis_id,
            status=ApprovalStatus.IN_REVIEW,
            current_step=1,
            current_stage=1,
            total_steps=len(plan),
            workflow_type="bill",
            execution_mode=execution_mode,
            document_amount=amount,
            document_type=doc.get("document_type") or "invoice",
            vendor_name=doc.get("vendor_name") or "Unknown vendor",
            risk_level=risk_level,
            initiated_by=initiator,
            initiated_at=now,
            due_date=due,
            escalation_due=due + timedelta(days=1),
            auto_approved=False,
            auto_rejected=False,
            is_urgent=False,
            metadata={"ap_automation": True, "routed_by_rules": not plan[0].metadata.get("fallback")},
        )

        steps = [
            ApprovalStep(
                id=uuid4(),
                workflow_id=workflow_id,
                org_id=org_id,
                step_number=planned.step_number,
                stage_number=1 if single_stage else planned.step_number,
                step_name=planned.step_name,
                approver_id=planned.approver_id,
                approver_role=planned.approver_role,
                approver_group_id=planned.approver_group_id,
                auto_escalated=planned.auto_escalated,
                spending_limit=planned.spending_limit,
                decision=ApprovalDecision.PENDING,  # overwritten by start_workflow per-stage
                due_date=due if planned.step_number == 1 else None,
                created_at=now,
            )
            for planned in plan
        ]

        created = await self.engine.start_workflow(workflow=workflow, steps=steps)

        self.db.table("documents").update({"status": "in_approval", "pipeline_stage": "approval", "ap_status": "awaiting_approval"}).eq("id", str(document_id)).eq("org_id", str(org_id)).execute()
        return created.id

    async def _apply_auto_decision(self, *, org_id: UUID, document_id: UUID, auto_decision):
        """
        Applies a rule-driven auto_approve/auto_reject/block decision
        without ever creating an approval workflow — the routing
        engine already decided, there's no human step to activate.
        Every transition still goes through InvoiceStateMachine, and
        still gets an audit_logs entry.
        """
        state = InvoiceStateMachine(self.db)
        current = await state.get_status(document_id)

        if current != InvoiceAPStatus.AWAITING_APPROVAL and state.can_transition(current, InvoiceAPStatus.AWAITING_APPROVAL):
            await state.transition(
                document_id, org_id, InvoiceAPStatus.AWAITING_APPROVAL,
                triggered_by="ap_routing_engine", reason=f"routed by rule {auto_decision.rule_id}",
            )

        target = {
            "approve": InvoiceAPStatus.APPROVED,
            "reject": InvoiceAPStatus.REJECTED,
            "block": InvoiceAPStatus.ON_HOLD,
        }[auto_decision.decision]

        await state.transition(
            document_id, org_id, target, triggered_by="ap_routing_engine",
            reason=auto_decision.reason or f"auto-{auto_decision.decision} (rule {auto_decision.rule_id})",
            metadata={"rule_id": str(auto_decision.rule_id)},
        )

        if self.engine.audit_service is not None:
            try:
                await self.engine.audit_service.log(
                    org_id=org_id, user_id=None, action=f"document.auto_{auto_decision.decision}",
                    resource_type="document", resource_id=document_id,
                    old_values={}, new_values={"decision": auto_decision.decision, "rule_id": str(auto_decision.rule_id)},
                )
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Failed to write audit_logs entry for auto-decision on %s", document_id)

        if auto_decision.decision == "approve":
            await BillSyncWorker().execute(document_id=document_id)

        return None  # no workflow was created — callers must treat a None workflow_id as "already decided"

    async def sync_after_decision(self, *, workflow_id: UUID, document_id: UUID, actor_id: UUID):
        """
        Applies AP side effects after ApprovalEngine.process_decision has
        already updated the workflow's authoritative status. Does not
        recompute completion itself.
        """
        workflow = self.db.table("approval_workflows").select("status,workflow_type").eq("id", str(workflow_id)).single().execute().data
        if not workflow:
            return "unknown"

        if workflow.get("workflow_type") == "payment":
            from app.services.payment.payment_approval_service import PaymentApprovalService
            org_row = self.db.table("approval_workflows").select("org_id").eq("id", str(workflow_id)).single().execute().data
            org_id = UUID(org_row["org_id"]) if org_row else None
            if org_id is None:
                return "unknown"
            return await PaymentApprovalService(self.db).on_workflow_decided(org_id=org_id, workflow_id=workflow_id, actor_id=actor_id)

        status = workflow.get("status")

        if status == "rejected":
            self.db.table("documents").update({"status": "rejected", "ap_status": "rejected"}).eq("id", str(document_id)).execute()
            return "rejected"

        if status == "approved":
            self.db.table("documents").update({"status": "approved", "pipeline_stage": "complete", "ap_status": "approved"}).eq("id", str(document_id)).execute()
            # Approval is the explicit event that starts ERP bill sync.
            # There is intentionally no scheduler fallback for AP bill sync.
            await BillSyncWorker().execute(document_id=document_id)
            return "approved"

        return "pending"
