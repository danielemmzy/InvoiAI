"use client";

import { useState } from "react";
import { CalendarClock, CheckCircle2, CircleAlert, History, Loader2, XCircle } from "lucide-react";
import { useCancelPaymentInstruction, usePaymentInstructionEvents, usePaymentInstructions, useReconcilePaymentInstruction, useScheduleDocumentPayment } from "@/hooks/useAP";
import type { PaymentInstruction, PaymentInstructionStatus } from "@/api/ap";

const STATUS: Record<PaymentInstructionStatus, { label: string; description: string }> = {
  requested: { label: "Requested", description: "Payment request created; approval workflow is being prepared." },
  scheduled: { label: "Scheduled", description: "Payment is queued for its planned date." },
  pending_approval: { label: "Awaiting payment approval", description: "Payment approval is still in progress." },
  approved_for_payment: { label: "Approved for payment", description: "Payment approval is complete; compliance checks are next." },
  pending_authorization: { label: "Authorization review", description: "Payment is waiting for compliance authorization." },
  authorized: { label: "Authorized", description: "Compliance checks passed; provider submission is next." },
  blocked: { label: "Blocked", description: "Resolve the listed compliance or approval issue before release." },
  processing: { label: "Processing", description: "The provider has accepted the payment. Final settlement is not yet confirmed." },
  paid: { label: "Paid", description: "The provider has confirmed payment; reconciliation may still be pending." },
  returned: { label: "Returned", description: "The provider reported a returned or reversed payment. Review before retrying." },
  failed: { label: "Failed", description: "The provider reported failure. Review the reason before creating a new payment attempt." },
  cancelled: { label: "Cancelled", description: "This payment instruction was cancelled." },
  reconciled: { label: "Paid & reconciled", description: "Provider status has been checked and reconciled." },
};

function money(amount: number, currency: string) {
  try { return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount); }
  catch { return `${currency} ${amount.toLocaleString()}`; }
}

function Activity({ instructionId }: { instructionId: string }) {
  const events = usePaymentInstructionEvents(instructionId);
  if (events.isLoading) return <p className="muted" style={{ fontSize: 12 }}>Loading payment activity…</p>;
  if (!events.data?.length) return <p className="muted" style={{ fontSize: 12 }}>No activity recorded yet.</p>;
  return <ol style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 8 }}>
    {events.data.map((event) => <li key={event.id} style={{ fontSize: 12, color: "#575249" }}>
      <strong>{event.from_status ? `${event.from_status.replaceAll("_", " ")} → ` : ""}{event.to_status.replaceAll("_", " ")}</strong>
      {event.reason ? <span> · {event.reason}</span> : null}
      <div className="muted">{new Date(event.created_at).toLocaleString()}</div>
    </li>)}
  </ol>;
}

function InstructionCard({ instruction, documentId }: { instruction: PaymentInstruction; documentId: string }) {
  const [reason, setReason] = useState("");
  const [showActivity, setShowActivity] = useState(false);
  const cancel = useCancelPaymentInstruction(documentId);
  const reconcile = useReconcilePaymentInstruction(documentId);
  const meta = STATUS[instruction.status] ?? STATUS.requested;
  const canCancel = ["requested", "scheduled", "pending_approval", "approved_for_payment", "pending_authorization", "authorized", "processing", "blocked"].includes(instruction.status);
  const canReconcile = ["processing", "paid"].includes(instruction.status) && !!instruction.provider_payment_id;
  return <div style={{ border: "1px solid #E5E0D7", borderRadius: 12, padding: 14, marginTop: 10 }}>
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
      <div><div style={{ fontWeight: 700 }}>{meta.label}</div><div className="muted" style={{ fontSize: 12, marginTop: 3 }}>{meta.description}</div></div>
      <div style={{ fontWeight: 700 }}>{money(instruction.amount, instruction.currency)}</div>
    </div>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 12, fontSize: 12, color: "#6B6860" }}>
      <span><CalendarClock size={13} style={{ verticalAlign: "-2px", marginRight: 4 }} />{instruction.scheduled_date || "No scheduled date"}</span>
      <span>Method: {instruction.payment_method || "Not specified"}</span>
      <span>Provider: {instruction.provider || "Not submitted"}</span>
      {instruction.provider_payment_id && <span>Reference: {instruction.provider_payment_id}</span>}
    </div>
    {instruction.failure_reason && <div style={{ marginTop: 10, color: "#9D3129", fontSize: 12 }}><CircleAlert size={13} style={{ verticalAlign: "-2px", marginRight: 5 }} />{instruction.failure_reason}</div>}
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
      <button className="btn-quiet" type="button" onClick={() => setShowActivity((v) => !v)}><History size={13} style={{ verticalAlign: "-2px", marginRight: 5 }} />{showActivity ? "Hide activity" : "View activity"}</button>
      {canCancel && <>
        <input aria-label="Cancellation reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason to cancel" style={{ maxWidth: 220, minWidth: 150 }} />
        <button className="btn-secondary" type="button" disabled={reason.trim().length < 3 || cancel.isPending} onClick={() => cancel.mutate({ instructionId: instruction.id, reason: reason.trim() })}>
          {cancel.isPending ? <Loader2 size={13} className="spin" /> : <XCircle size={13} />} Cancel payment
        </button>
      </>}
      {canReconcile && <button className="btn-primary" type="button" disabled={reconcile.isPending} onClick={() => reconcile.mutate(instruction.id)}>{reconcile.isPending ? <Loader2 size={13} className="spin" /> : <CheckCircle2 size={13} />} Check provider status & reconcile</button>}
      {!["requested", "scheduled", "pending_approval", "approved_for_payment", "pending_authorization", "authorized", "blocked", "processing"].includes(instruction.status) && instruction.status !== "reconciled" && <span className="muted" style={{ alignSelf: "center", fontSize: 12 }}>A new payment attempt can be requested after the failure or return is reviewed.</span>}
    </div>
    {showActivity && <div style={{ borderTop: "1px solid #E5E0D7", marginTop: 12, paddingTop: 12 }}><Activity instructionId={instruction.id} /></div>}
  </div>;
}

export default function PaymentLifecyclePanel({ documentId, apStatus }: { documentId: string; apStatus?: string | null }) {
  const query = usePaymentInstructions(documentId);
  const schedule = useScheduleDocumentPayment();
  const [showRequest, setShowRequest] = useState(false);
  const [scheduledDate, setScheduledDate] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("ach");
  const [requestKey, setRequestKey] = useState("");
  const canStart = apStatus === "payment_ready" && !query.data?.some((i) => !["failed", "returned", "cancelled", "reconciled"].includes(i.status));
  const showPanel = ["payment_ready", "paid", "reconciled"].includes(apStatus || "") || !!query.data?.length;
  if (!showPanel) return null;
  return <section className="card" style={{ marginBottom: 16, padding: 20 }}>
    <div className="section-card-header">
      <div><div className="section-card-name">Payment</div><p className="muted" style={{ margin: "5px 0 0", fontSize: 12 }}>Approval, compliance, provider confirmation and reconciliation are tracked separately.</p></div>
      {canStart && <button className="btn-primary" type="button" onClick={() => { const next = !showRequest; setShowRequest(next); if (next) setRequestKey(`doc:${documentId}:${crypto.randomUUID()}`); }} disabled={schedule.isPending}>{schedule.isPending ? <Loader2 size={14} /> : <CalendarClock size={14} />} {showRequest ? "Close" : query.data?.some((i) => ["failed", "returned", "cancelled"].includes(i.status)) ? "Retry payment" : "Request payment"}</button>}
    </div>
    {showRequest && <div style={{ padding: 12, border: "1px solid #E5E0D7", borderRadius: 10, marginTop: 12 }}>
      <p style={{ fontSize: 13, marginTop: 0 }}>This starts a payment attempt and its separate approval/compliance workflow. If this is a retry, a new attempt is created; the bill is not marked paid until the provider confirms success.</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 10, marginBottom: 12 }}>
        <label style={{ fontSize: 12 }}>Payment method<select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)} style={{ display: "block", width: "100%", marginTop: 5 }}><option value="ach">ACH / bank transfer</option><option value="wire">Wire</option><option value="check">Check</option><option value="other">Other</option></select></label>
        <label style={{ fontSize: 12 }}>Preferred payment date<input type="date" min={new Date().toISOString().slice(0, 10)} value={scheduledDate} onChange={(e) => setScheduledDate(e.target.value)} style={{ display: "block", width: "100%", marginTop: 5 }} /></label>
      </div>
      <div style={{ display: "flex", gap: 8 }}><button className="btn-primary" type="button" disabled={schedule.isPending} onClick={() => schedule.mutate({ documentId, payment_method: paymentMethod, scheduled_date: scheduledDate || undefined, idempotency_key: requestKey || `doc:${documentId}` }, { onSuccess: () => { setShowRequest(false); setRequestKey(""); } })}>Confirm request</button><button className="btn-secondary" type="button" onClick={() => setShowRequest(false)}>Cancel</button></div>
    </div>}
    {query.isLoading ? <p className="muted" style={{ fontSize: 12 }}>Loading payment status…</p> : query.isError ? <p style={{ color: "#9D3129", fontSize: 12 }}>Could not load payment status. Refresh the page to retry.</p> : query.data?.length ? query.data.map((item) => <InstructionCard key={item.id} instruction={item} documentId={documentId} />) : <p className="muted" style={{ fontSize: 13 }}>No payment instruction has been created for this bill yet.</p>}
  </section>;
}
