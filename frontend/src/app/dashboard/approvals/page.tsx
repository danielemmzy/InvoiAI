"use client";
// Approvals — /dashboard/approvals

import { useState } from "react";
import Link from "next/link";
import { CheckCircle2, XCircle, Clock3, ShieldAlert, ExternalLink, Loader2 } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError, EmptyState } from "@/components/ui/PageState";
import { usePendingApprovals, useDecideApproval } from "@/hooks/useApprovalsInsightsPO";
import type { ApprovalQueueItem } from "@/api/approvals";

function money(n: number, currency = "USD") {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
  } catch {
    return `$${Math.round(n).toLocaleString()}`;
  }
}

function fmtDate(d: string | null) {
  if (!d) return "No due date";
  const date = new Date(d);
  return Number.isNaN(date.getTime()) ? d : date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function ApprovalsPage() {
  const [tab, setTab] = useState<"pending" | "overdue">("pending");
  const pending = usePendingApprovals();
  const decide = useDecideApproval();
  const [comment, setComment] = useState<Record<string, string>>({});

  const query = pending; // overdue reuses the same list endpoint filtered client-side for now
  const items = tab === "overdue"
    ? (query.data ?? []).filter((i) => i.due_date && new Date(i.due_date) < new Date())
    : query.data ?? [];

  return (
    <DashboardLayout>
      <div className="page-head">
        <div>
          <div className="eyebrow">Accounts payable</div>
          <h1 className="page-title">Approvals</h1>
          <p className="page-subtitle">Everything routed to you, ranked by how urgent it is.</p>
        </div>
        <div className="ap-subnav">
          <button type="button" className={`ap-subnav-item${tab === "pending" ? " active" : ""}`} onClick={() => setTab("pending")}>Pending</button>
          <button type="button" className={`ap-subnav-item${tab === "overdue" ? " active" : ""}`} onClick={() => setTab("overdue")}>Overdue</button>
        </div>
      </div>

      {query.isLoading ? (
        <PageLoading variant="table" rows={6} />
      ) : query.isError ? (
        <PageError title="Couldn't load your approval queue" onRetry={query.refetch} />
      ) : !items.length ? (
        <EmptyState
          icon={CheckCircle2}
          title={tab === "overdue" ? "Nothing overdue" : "Nothing waiting on you"}
          message={tab === "overdue" ? "No pending approval has slipped past its due date." : "New invoices will land here as soon as they're routed to you."}
        />
      ) : (
        <div className="approval-list">
          {items.map((item) => (
            <ApprovalCard key={item.step_id} item={item} decide={decide} comment={comment[item.step_id] ?? ""} setComment={(v) => setComment((c) => ({ ...c, [item.step_id]: v }))} />
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}

function ApprovalCard({
  item, decide, comment, setComment,
}: {
  item: ApprovalQueueItem;
  decide: ReturnType<typeof useDecideApproval>;
  comment: string;
  setComment: (v: string) => void;
}) {
  const tone = item.risk_level === "high" ? "danger" : item.risk_level === "medium" ? "warn" : item.risk_level === "low" ? "good" : "neutral";
  const isDeciding = decide.isPending && decide.variables?.stepId === item.step_id;

  return (
    <div className={`approval-card${item.is_urgent ? " urgent" : ""}`}>
      <div className="approval-card-top">
        <div>
          <div className="approval-card-vendor">{item.vendor_name || "Unknown vendor"}</div>
          <div className="approval-card-meta">
            {item.document_number || "No invoice #"} · {item.step_name} · Step {item.step_number}
          </div>
        </div>
        <div className="approval-card-amount serif">{money(item.total_amount, item.currency)}</div>
      </div>

      <div className="approval-card-meta-row">
        <span className={`status-pill ${tone}`}>
          <ShieldAlert size={11} style={{ verticalAlign: -1, marginRight: 3 }} />
          {item.risk_level ? `${item.risk_level} risk` : "Analysis pending"} · {item.health_score ?? "—"}/100
        </span>
        <span className="approval-card-due">
          <Clock3 size={12} /> {fmtDate(item.due_date)}
        </span>
        {item.is_urgent && <span className="status-pill danger">Urgent</span>}
      </div>

      <input
        type="text"
        className="approval-comment-input"
        placeholder="Add a comment (optional)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
      />

      <div className="approval-card-actions">
        <Link href={`/dashboard/document/${item.document_id}`} className="btn-secondary">
          <ExternalLink size={13} /> Review document
        </Link>
        <button
          type="button"
          className="btn-danger-outline"
          disabled={isDeciding}
          onClick={() => decide.mutate({ stepId: item.step_id, decision: "rejected", comment: comment || undefined })}
        >
          <XCircle size={14} /> Reject
        </button>
        <button
          type="button"
          className="btn-primary"
          disabled={isDeciding}
          onClick={() => decide.mutate({ stepId: item.step_id, decision: "approved", comment: comment || undefined })}
        >
          {isDeciding ? <Loader2 size={14} className="spin" /> : <CheckCircle2 size={14} />} Approve
        </button>
      </div>
    </div>
  );
}
