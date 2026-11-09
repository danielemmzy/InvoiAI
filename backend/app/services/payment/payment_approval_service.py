"""
============================================================
Payment Approval Service

Implements the P0 pipeline:

  Approved bill -> payment instruction requested
    -> payment approval workflow (payment_approval_limit,
       supervisor escalation, same ApprovalEngine as bills,
       workflow_type="payment")
    -> payment authorization / compliance gate
       (PaymentAuthorizationService — W-9, bank-change, payment
       hold, open exceptions)
    -> AUTHORIZED -> handed to PaymentInstructionService.execute()
       (provider-agnostic payment execution)

This is deliberately a *second*, independent approval pass from
the bill-approval workflow — a different scope (payment vs bill)
routed through the same rules engine and the same canonical
ApprovalEngine, per the "one execution engine" requirement.
Nothing here inserts approval_workflows/approval_steps directly.
============================================================
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.enum.ap import ApprovalRuleScope, PaymentAuthorizationStatus, PaymentInstructionStatus
from app.core.enum.application import ApprovalStatus
from app.core.enum.database import ApprovalDecision, RiskLevel
from app.core.supabase import get_supabase
from app.models.domain.approval import ApprovalStep, ApprovalWorkflow
from app.repositories.approval.history_repository import ApprovalHistoryRepository
from app.repositories.approval.step_repository import ApprovalStepRepository
from app.repositories.approval.workflow_repository import ApprovalWorkflowRepository
from app.repositories.audit.audit_repository import AuditRepository
from app.services.ap.approval_bridge import document_routing_dimensions
from app.services.ap.routing_engine import APRoutingEngine
from app.services.approval.approval_engine import ApprovalEngine
from app.services.audit_service import AuditService
from app.services.payment.payment_authorization_service import PaymentAuthorizationService
from app.services.payment.payment_instruction_service import PaymentInstructionService


class PaymentApprovalService:

    def __init__(
        self,
        db=None,
        routing_engine: APRoutingEngine | None = None,
        instructions: PaymentInstructionService | None = None,
        authorization: PaymentAuthorizationService | None = None,
    ) -> None:
        self.db = db or get_supabase()
        self.routing_engine = routing_engine or APRoutingEngine(self.db)
        self.instructions = instructions or PaymentInstructionService(self.db)
        self.authorization = authorization or PaymentAuthorizationService(self.db)
        self.engine = ApprovalEngine(
            ApprovalWorkflowRepository(),
            ApprovalStepRepository(),
            ApprovalHistoryRepository(),
            audit_service=AuditService(repository=AuditRepository()),
        )

    # =========================================================
    # Initiate: bill approved -> request a payment + start its
    # approval workflow (idempotent on document_id).
    # =========================================================

    async def initiate(
        self, *, org_id: UUID, document_id: UUID, requested_by: UUID | None,
        idempotency_key: str | None = None, payment_method: str | None = None,
        scheduled_date: str | None = None,
    ):

        instruction = await self.instructions.get_or_create(
            org_id=org_id, document_id=document_id, requested_by=requested_by,
            idempotency_key=idempotency_key, payment_method=payment_method,
            scheduled_date=scheduled_date,
        )

        if instruction.status != PaymentInstructionStatus.REQUESTED:
            # Already in flight (or further along) — idempotent no-op.
            return instruction

        existing_workflow = (
            self.db.table("approval_workflows").select("id")
            .eq("org_id", str(org_id)).eq("document_id", str(document_id)).eq("workflow_type", "payment")
            .eq("status", ApprovalStatus.IN_REVIEW.value)
            .limit(1).execute().data
        )

        if existing_workflow:
            workflow_id = UUID(existing_workflow[0]["id"])
        else:
            workflow_id = await self._start_payment_workflow(
                org_id=org_id, document_id=document_id, instruction_id=instruction.id, requested_by=requested_by,
            )
            if workflow_id is None:
                # A rule short-circuited with block/auto_approve/auto_reject —
                # _start_payment_workflow already applied it to the instruction.
                return await self.instructions.repository.get(instruction.id)

        return await self.instructions.transition(
            org_id=org_id, instruction_id=instruction.id,
            to_status=PaymentInstructionStatus.PENDING_APPROVAL,
            actor_id=requested_by, reason="payment approval workflow started",
            approval_workflow_id=str(workflow_id),
        )

    async def _start_payment_workflow(self, *, org_id: UUID, document_id: UUID, instruction_id: UUID, requested_by: UUID | None) -> UUID | None:

        doc = (
            self.db.table("documents").select("total_amount,document_type,vendor_name,vendor_id,external_source_data,capture_overrides")
            .eq("org_id", str(org_id)).eq("id", str(document_id)).single().execute().data
        )
        amount = Decimal(str(doc.get("total_amount") or 0))
        vendor_id = UUID(doc["vendor_id"]) if doc.get("vendor_id") else None
        department, cost_center, location = document_routing_dimensions(doc)

        plan, execution_mode, auto_decision = await self.routing_engine.build_plan(
            org_id=org_id, amount=amount, vendor_id=vendor_id,
            department=department, cost_center=cost_center, location=location,
            document_type=doc.get("document_type"), risk_level=RiskLevel.MEDIUM.value, requires_po=None,
            scope=ApprovalRuleScope.PAYMENT,
        )

        if auto_decision is not None:
            await self._apply_auto_decision(org_id=org_id, instruction_id=instruction_id, auto_decision=auto_decision, actor_id=requested_by)
            return None

        if not plan:
            raise ValueError("No active payment approver is configured for this organization.")

        initiator = requested_by or next((s.approver_id for s in plan if s.approver_id), None)
        if initiator is None:
            raise ValueError("Unable to determine an initiator for this payment approval workflow.")

        now = datetime.now(UTC)
        workflow_id = uuid4()
        single_stage = execution_mode in ("parallel", "any_one")

        workflow = ApprovalWorkflow(
            id=workflow_id, org_id=org_id, document_id=document_id, analysis_id=None,
            status=ApprovalStatus.IN_REVIEW, current_step=1, current_stage=1, total_steps=len(plan),
            workflow_type="payment", execution_mode=execution_mode, document_amount=amount,
            document_type=doc.get("document_type") or "invoice", vendor_name=doc.get("vendor_name") or "Unknown vendor",
            risk_level=RiskLevel.MEDIUM.value, initiated_by=initiator, initiated_at=now,
            due_date=now + timedelta(days=2), escalation_due=now + timedelta(days=3),
            auto_approved=False, auto_rejected=False, is_urgent=False,
            metadata={"ap_automation": True, "payment_instruction_id": str(instruction_id)},
        )

        steps = [
            ApprovalStep(
                id=uuid4(), workflow_id=workflow_id, org_id=org_id,
                step_number=planned.step_number,
                stage_number=1 if single_stage else planned.step_number,
                step_name=planned.step_name, approver_id=planned.approver_id,
                approver_role=planned.approver_role, approver_group_id=planned.approver_group_id,
                auto_escalated=planned.auto_escalated, spending_limit=planned.spending_limit,
                decision=ApprovalDecision.PENDING,
                created_at=now,
            )
            for planned in plan
        ]

        created = await self.engine.start_workflow(workflow=workflow, steps=steps)
        return created.id

    # =========================================================
    # React to a completed/rejected payment approval workflow
    # (called from approval_bridge.sync_after_decision).
    # =========================================================

    async def _apply_auto_decision(self, *, org_id: UUID, instruction_id: UUID, auto_decision, actor_id: UUID | None) -> None:
        """
        A payment routing rule short-circuited with block/auto_approve/
        auto_reject — no approval workflow needed. auto_approve still
        goes through the compliance gate (PaymentAuthorizationService)
        before execution; it is not a bypass of those checks, only of
        the human approval step.
        """
        if auto_decision.decision == "reject":
            await self.instructions.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=PaymentInstructionStatus.CANCELLED,
                actor_id=actor_id, reason=auto_decision.reason or f"auto-rejected (rule {auto_decision.rule_id})",
            )
            return

        if auto_decision.decision == "block":
            await self.instructions.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=PaymentInstructionStatus.BLOCKED,
                actor_id=actor_id, reason=auto_decision.reason or f"auto-blocked (rule {auto_decision.rule_id})",
            )
            return

        # auto_approve
        await self.instructions.transition(
            org_id=org_id, instruction_id=instruction_id,
            to_status=PaymentInstructionStatus.APPROVED_FOR_PAYMENT,
            actor_id=actor_id, reason=f"auto-approved (rule {auto_decision.rule_id})", approved_by=str(actor_id) if actor_id else None,
        )

        instruction = await self.instructions.repository.get(instruction_id)
        auth = await self.authorization.evaluate(org_id=org_id, document_id=instruction.document_id)

        if auth.status == PaymentAuthorizationStatus.AUTHORIZED:
            instruction = await self.instructions.repository.get(instruction_id)
            scheduled = instruction.scheduled_date and instruction.scheduled_date > datetime.now(UTC).date()
            target = PaymentInstructionStatus.SCHEDULED if scheduled else PaymentInstructionStatus.AUTHORIZED
            await self.instructions.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=target,
                actor_id=actor_id, reason=("approved and held until scheduled date" if scheduled else "compliance checks passed"),
                authorized_by=str(actor_id) if actor_id else None,
            )
            if not scheduled:
                await self.instructions.execute(org_id=org_id, instruction_id=instruction_id, actor_id=actor_id)
        else:
            await self.instructions.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=PaymentInstructionStatus.BLOCKED,
                actor_id=actor_id, reason="; ".join(auth.blocked_reasons) or "blocked by compliance checks",
            )

    async def on_workflow_decided(self, *, org_id: UUID, workflow_id: UUID, actor_id: UUID) -> str:

        workflow = self.db.table("approval_workflows").select("status,document_id").eq("id", str(workflow_id)).single().execute().data
        if not workflow:
            return "unknown"

        rows = (
            self.db.table("payment_instructions").select("id")
            .eq("org_id", str(org_id)).eq("approval_workflow_id", str(workflow_id)).limit(1).execute().data
        )
        if not rows:
            return "no_instruction"

        instruction_id = UUID(rows[0]["id"])

        if workflow["status"] == "rejected":
            await self.instructions.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=PaymentInstructionStatus.CANCELLED, actor_id=actor_id, reason="payment approval rejected",
            )
            return "cancelled"

        if workflow["status"] != "approved":
            return "pending"

        await self.instructions.transition(
            org_id=org_id, instruction_id=instruction_id,
            to_status=PaymentInstructionStatus.APPROVED_FOR_PAYMENT,
            actor_id=actor_id, reason="payment approval workflow completed", approved_by=str(actor_id),
        )

        document_id = UUID(workflow["document_id"])
        auth = await self.authorization.evaluate(org_id=org_id, document_id=document_id)

        if auth.status == PaymentAuthorizationStatus.AUTHORIZED:
            instruction = await self.instructions.repository.get(instruction_id)
            scheduled = instruction.scheduled_date and instruction.scheduled_date > datetime.now(UTC).date()
            target = PaymentInstructionStatus.SCHEDULED if scheduled else PaymentInstructionStatus.AUTHORIZED
            await self.instructions.transition(
                org_id=org_id, instruction_id=instruction_id,
                to_status=target,
                actor_id=actor_id, reason=("approved and held until scheduled date" if scheduled else "compliance checks passed"),
                authorized_by=str(actor_id),
            )
            if not scheduled:
                await self.instructions.execute(org_id=org_id, instruction_id=instruction_id, actor_id=actor_id)
            return "scheduled" if scheduled else "authorized"

        await self.instructions.transition(
            org_id=org_id, instruction_id=instruction_id,
            to_status=PaymentInstructionStatus.BLOCKED,
            actor_id=actor_id, reason="; ".join(auth.blocked_reasons) or "blocked by compliance checks",
        )
        return "blocked"
