"use client";
// Payment queue — /dashboard/ap/payments
// Bills that cleared approval and are waiting on payment release,
// each shown with its own payment authorization status — separate
// from the bill approval that already happened. Blocked rows can
// be overridden (with a required reason) by a user with the
// override permission.

import { useState } from "react";
import Link from "next/link";
import { X, ShieldAlert, RotateCcw, CheckCircle2, Clock3, CircleAlert } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError, EmptyState } from "@/components/ui/PageState";
import { usePaymentQueue, useEvaluatePaymentAuthorization, useOverridePaymentBlock } from "@/hooks/useAP";
import type { PaymentQueueRow, PaymentAuthorizationStatus } from "@/api/ap";

function money(n: number | null, currency = "USD") {
  if (n == null) return "—";
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(n);
  } catch {
    return `$${n.toLocaleString()}`;
  }
}

const STATUS_META: Record<PaymentAuthorizationStatus, { label: string; tone: string }> = {
  authorized: { label: "Authorized", tone: "good" },
  blocked: { label: "Blocked", tone: "danger" },
  needs_review: { label: "Needs review", tone: "warn" },
  override_required: { label: "Override required", tone: "danger" },
};

function StatusPill({ status }: { status: PaymentAuthorizationStatus }) {
  const meta = STATUS_META[status] ?? STATUS_META.needs_review;
  return <span className={`status-pill ${meta.tone}`}>{meta.label}</span>;
}

function OverrideDrawer({ row, onClose }: { row: PaymentQueueRow; onClose: () => void }) {
  const [reason, setReason] = useState("");
  const override = useOverridePaymentBlock();

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer-panel" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Override payment block">
        <div className="drawer-head">
          <div>
            <div className="panel-kicker">Override payment block</div>
            <h2 className="serif">{row.vendor_name ?? "Unknown vendor"}</h2>
          </div>
          <button className="drawer-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        <div className="drawer-amount">{money(row.amount, row.currency ?? undefined)}</div>

        <div className={"drawer-risk-note high"}>
          <ShieldAlert size={15} />
          This overrides the compliance block for this bill. If a payment instruction is already blocked, InvoiAI will attempt to submit it; otherwise this records authorization only. The decision is audited with your name and reason.
        </div>

        {row.blocked_reasons.length > 0 && (
          <ul className="modal-reason-list">
            {row.blocked_reasons.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        )}

        <textarea
          className="modal-textarea"
          placeholder="Why is this override justified?"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
        />

        <div className="drawer-actions">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn-danger-outline"
            disabled={!reason.trim() || override.isPending}
            onClick={() => override.mutate({ documentId: row.document_id, reason: reason.trim() }, { onSuccess: onClose })}
          >
            {override.isPending ? "Releasing…" : "Override & release payment"}
          </button>
        </div>
      </aside>
    </div>
  );
}

export default function PaymentQueuePage() {
  const queue = usePaymentQueue();
  const evaluate = useEvaluatePaymentAuthorization();
  const [overrideRow, setOverrideRow] = useState<PaymentQueueRow | null>(null);

  const rows = queue.data ?? [];
  const readyRows = rows.filter((row) => row.authorization_status === "authorized");
  const reviewRows = rows.filter((row) => row.authorization_status === "needs_review");
  const blockedRows = rows.filter((row) => row.authorization_status === "blocked" || row.authorization_status === "override_required");
  const readyAmount = readyRows.reduce((total, row) => total + (row.amount ?? 0), 0);

  return (
    <DashboardLayout>
      <div className="page-head payment-queue-head">
        <div>
          <div className="eyebrow">Accounts payable</div>
          <h1 className="page-title">Payment queue</h1>
          <p className="page-subtitle">Release only the bills that have cleared their own authorization and compliance checks.</p>
        </div>
        <div className="ap-subnav">
          <Link href="/dashboard/ap" className="ap-subnav-item">Overview</Link>
          <Link href="/dashboard/ap/aging" className="ap-subnav-item">Aging analysis</Link>
          <Link href="/dashboard/ap/exceptions" className="ap-subnav-item">Exceptions</Link>
          <Link href="/dashboard/ap/payments" className="ap-subnav-item active">Payments</Link>
          <Link href="/dashboard/settings/ap-rules" className="ap-subnav-item">AP settings</Link>
        </div>
      </div>

      {queue.isLoading ? (
        <PageLoading variant="table" />
      ) : queue.isError ? (
        <PageError onRetry={queue.refetch} />
      ) : !queue.data?.length ? (
        <EmptyState title="Nothing waiting on payment" message="Every approved bill has been paid or has no payment pending." />
      ) : (
        <>
          <section className="payment-queue-summary" aria-label="Payment queue summary">
            <div className="payment-summary-card ready">
              <CheckCircle2 size={18} aria-hidden="true" />
              <span>Ready to release</span>
              <strong>{money(readyAmount)}</strong>
              <small>{readyRows.length} bill{readyRows.length === 1 ? "" : "s"} cleared</small>
            </div>
            <div className="payment-summary-card review">
              <Clock3 size={18} aria-hidden="true" />
              <span>Needs review</span>
              <strong>{reviewRows.length}</strong>
              <small>Awaiting a decision</small>
            </div>
            <div className="payment-summary-card blocked">
              <CircleAlert size={18} aria-hidden="true" />
              <span>Blocked</span>
              <strong>{blockedRows.length}</strong>
              <small>Protection remains active</small>
            </div>
          </section>

          <div className="payment-release-list" aria-label="Bills awaiting payment">
            <div className="payment-release-list-head">
              <span>Bill</span>
              <span>Release status</span>
            </div>
            {rows.map((row) => (
              <article key={row.document_id} className="payment-release-row">
                <div className="payment-release-bill">
                  <span className="payment-release-vendor">{row.vendor_name ?? "Unknown vendor"}</span>
                  <Link href={`/dashboard/document/${row.document_id}`} className="payment-release-invoice" title="Open bill and payment workspace">
                    {row.document_number ?? row.document_id.slice(0, 8)}
                  </Link>
                  <span className="payment-release-due">Due {row.due_date ?? "not set"}</span>
                </div>
                <strong className="payment-release-amount">{money(row.amount, row.currency ?? undefined)}</strong>
                <div className="payment-release-status">
                  <StatusPill status={row.authorization_status} />
                  {row.blocked_reasons.length > 0 && <span>{row.blocked_reasons.join(" · ")}</span>}
                </div>
                <div className="payment-release-actions">
                  <button type="button" className="btn-quiet" title="Re-check authorization" onClick={() => evaluate.mutate(row.document_id)}>
                    <RotateCcw size={14} /><span>Re-check</span>
                  </button>
                  {(row.authorization_status === "blocked" || row.authorization_status === "override_required") && (
                    <button type="button" className="btn-danger-outline" onClick={() => setOverrideRow(row)}>Review override</button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      {overrideRow && <OverrideDrawer row={overrideRow} onClose={() => setOverrideRow(null)} />}
    </DashboardLayout>
  );
}
