"use client";
// Vendor statement — /dashboard/vendors/[vendorId]

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ShieldAlert, ShieldCheck, Clock3, Wallet, CreditCard, FileStack } from "lucide-react";
import {
  ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell,
} from "recharts";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError, EmptyState } from "@/components/ui/PageState";
import { useVendorStatement, useVendorDocumentRequests, useRequestVendorDocument, useVerifyBankChange, useVendorCredits, useCreateVendorCredit, useCancelVendorCredit, useApplyVendorCredit } from "@/hooks/useAP";
import type { VendorDocumentRequest } from "@/api/ap";

const STATUS_COLORS = ["#1A1916", "#C8922A", "#8B6420", "#D8CFBB"];

function money(n: number | null | undefined, currency = "USD") {
  if (n === null || n === undefined) return "—";
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
  } catch {
    return `$${Math.round(n).toLocaleString()}`;
  }
}

function fmtDate(d: string | null | undefined) {
  if (!d) return "—";
  const date = new Date(d);
  return Number.isNaN(date.getTime()) ? d : date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function VendorStatementPage() {
  const params = useParams<{ vendorId: string }>();
  const statement = useVendorStatement(params.vendorId);
  const credits = useVendorCredits(params.vendorId);
  const createCredit = useCreateVendorCredit(params.vendorId);
  const cancelCredit = useCancelVendorCredit(params.vendorId);
  const applyCredit = useApplyVendorCredit(params.vendorId);
  const [creditForm, setCreditForm] = useState(false);
  const [creditAmount, setCreditAmount] = useState("");
  const [creditNumber, setCreditNumber] = useState("");
  const [creditReason, setCreditReason] = useState("");
  const [creditExpiry, setCreditExpiry] = useState("");
  const [creditNotes, setCreditNotes] = useState("");

  return (
    <DashboardLayout>
      <Link href="/dashboard/vendors" className="text-link" style={{ marginBottom: 16 }}>
        <ArrowLeft size={14} /> All vendors
      </Link>

      {statement.isLoading ? (
        <PageLoading />
      ) : statement.isError ? (
        <PageError title="Couldn't load this vendor's statement" onRetry={statement.refetch} />
      ) : !statement.data ? (
        <EmptyState title="Vendor not found" />
      ) : (
        <>
          <div className="page-head">
            <div>
              <div className="eyebrow">Vendor statement</div>
              <h1 className="page-title">{statement.data.vendor_name}</h1>
              <p className="page-subtitle">
                Everything owed, everything paid, and how this vendor's risk profile has trended.
              </p>
            </div>
            <div className={`drawer-risk-note ${statement.data.risk_level}`} style={{ marginBottom: 0 }}>
              {statement.data.risk_level === "low" ? <ShieldCheck size={15} /> : <ShieldAlert size={15} />}
              Risk score {statement.data.risk_score}/100
              {statement.data.fraud_flags > 0 && ` · ${statement.data.fraud_flags} fraud flag${statement.data.fraud_flags > 1 ? "s" : ""}`}
            </div>
          </div>

          <div className="ap-metric-grid" style={{ gridTemplateColumns: "repeat(6, 1fr)" }}>
            <ApMetric icon={<CreditCard />} label="Credit limit" value={statement.data.credit_limit ? money(statement.data.credit_limit, statement.data.currency) : "No limit set"} />
            <ApMetric icon={<Wallet />} label="Total purchases" value={money(statement.data.total_purchases, statement.data.currency)} />
            <ApMetric icon={<Wallet />} label="Total payments" value={money(statement.data.total_payments, statement.data.currency)} />
            <ApMetric icon={<Wallet />} label="Total balance" value={money(statement.data.total_balance, statement.data.currency)} tone={statement.data.total_balance > 0 ? "warn" : undefined} />
            <ApMetric icon={<FileStack />} label="Open invoices" value={statement.data.open_invoices} />
            <ApMetric icon={<Clock3 />} label="Avg overdue days" value={statement.data.avg_overdue_days} tone={statement.data.avg_overdue_days > 0 ? "danger" : undefined} />
          </div>

          <section className="ap-chart-panel" style={{ marginTop: 20 }}>
            <div className="ap-chart-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
              <div><div className="panel-kicker">Vendor credits</div><h2>Credit notes & applications</h2><p className="page-subtitle">Track issued credits, remaining value, expiry and bill applications.</p></div>
              <button className="btn-primary" onClick={() => setCreditForm((v) => !v)}>{creditForm ? "Close" : "Add vendor credit"}</button>
            </div>
            {creditForm && <form onSubmit={(e) => { e.preventDefault(); const amount = Number(creditAmount); if (!Number.isFinite(amount) || amount <= 0) return; createCredit.mutate({ amount, currency: statement.data?.currency || "USD", credit_number: creditNumber || undefined, reason: creditReason || undefined, expires_at: creditExpiry || undefined, notes: creditNotes || undefined }, { onSuccess: () => { setCreditForm(false); setCreditAmount(""); setCreditNumber(""); setCreditReason(""); setCreditExpiry(""); setCreditNotes(""); } }); }} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 10, marginBottom: 18 }}>
              <label>Credit amount<input required type="number" min="0.01" step="0.01" value={creditAmount} onChange={(e) => setCreditAmount(e.target.value)} /></label>
              <label>Credit note number<input value={creditNumber} onChange={(e) => setCreditNumber(e.target.value)} maxLength={100} /></label>
              <label>Reason<input value={creditReason} onChange={(e) => setCreditReason(e.target.value)} placeholder="Return, pricing adjustment…" /></label>
              <label>Expires on<input type="date" min={new Date().toISOString().slice(0,10)} value={creditExpiry} onChange={(e) => setCreditExpiry(e.target.value)} /></label>
              <label style={{ gridColumn: "1 / -1" }}>Notes<textarea value={creditNotes} onChange={(e) => setCreditNotes(e.target.value)} rows={2} maxLength={4000} /></label>
              <div><button className="btn-primary" type="submit" disabled={createCredit.isPending || !creditAmount}>{createCredit.isPending ? "Saving…" : "Save credit"}</button></div>
            </form>}
            {credits.isLoading ? <p>Loading credits…</p> : credits.isError ? <p>Could not load vendor credits. Refresh to retry.</p> : !credits.data?.length ? <EmptyState title="No vendor credits yet" message="Create a credit note to track its available balance and apply it to an open bill." /> : <div style={{ overflowX: "auto" }}><table style={{ width: "100%", borderCollapse: "collapse" }}><thead><tr><th align="left">Credit note</th><th align="left">Issued</th><th align="left">Expires</th><th align="right">Original</th><th align="right">Available</th><th align="left">Status</th><th align="left">Actions</th></tr></thead><tbody>{credits.data.map((c) => <tr key={c.id} style={{ borderTop: "1px solid var(--border, #e5e1d8)" }}><td style={{ padding: "12px 6px" }}><strong>{c.credit_number || "Credit note"}</strong><div>{c.reason || c.notes || "—"}</div></td><td>{fmtDate(c.issued_at)}</td><td>{fmtDate(c.expires_at)}</td><td align="right">{money(Number(c.amount), c.currency)}</td><td align="right">{money(Number(c.remaining_amount), c.currency)}</td><td>{c.status.replaceAll("_", " ")}</td><td>{(c.status === "open" || c.status === "partially_applied") && Number(c.remaining_amount) > 0 && <><button className="btn-secondary" disabled={applyCredit.isPending} onClick={() => { const document_id = window.prompt("Enter the bill document ID to apply this credit to:"); if (!document_id?.trim()) return; const amountText = window.prompt(`Available credit: ${money(Number(c.remaining_amount), c.currency)}. Enter amount to apply:`); const amount = Number(amountText); if (Number.isFinite(amount) && amount > 0) applyCredit.mutate({ creditId: c.id, document_id: document_id.trim(), amount }); }}>Apply to bill</button>{Number(c.remaining_amount) === Number(c.amount) && <button className="btn-secondary" disabled={cancelCredit.isPending} onClick={() => { const reason = window.prompt("Why are you cancelling this credit?"); if (reason?.trim()) cancelCredit.mutate({ creditId: c.id, reason: reason.trim() }); }}>Cancel</button>}</>}{c.applications?.length ? <details><summary>{c.applications.length} application(s)</summary>{c.applications.map((a) => <div key={a.id}>Bill {a.document_id.slice(0,8)} · {money(Number(a.amount), a.currency)} · {fmtDate(a.created_at)}</div>)}{c.events?.map((ev: {id:string;event_type:string;created_at:string;details?:Record<string,unknown>}) => <div key={ev.id}>{ev.event_type.replaceAll("_", " ")} · {fmtDate(ev.created_at)}</div>)}</details> : c.events?.length ? <details><summary>Activity ({c.events.length})</summary>{c.events.map((ev: {id:string;event_type:string;created_at:string}) => <div key={ev.id}>{ev.event_type.replaceAll("_", " ")} · {fmtDate(ev.created_at)}</div>)}</details> : null}</td></tr>)}</tbody></table></div>}
          </section>

          <div className="ap-chart-grid" style={{ gridTemplateColumns: "1.6fr 1fr" }}>
            <div className="ap-chart-panel wide">
              <div className="ap-chart-head">
                <div><div className="panel-kicker">Trend</div><h2>Billed vs. paid</h2></div>
              </div>
              {!statement.data.trend.length ? (
                <EmptyState title="No history yet" />
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <ComposedChart data={statement.data.trend} margin={{ left: -12, right: 8, top: 8 }}>
                    <CartesianGrid stroke="#E2DDD4" vertical={false} />
                    <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#AAA8A0" }} axisLine={{ stroke: "#E2DDD4" }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#AAA8A0" }} axisLine={false} tickLine={false} width={54} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
                    <Tooltip contentStyle={{ borderRadius: 10, border: "0.5px solid #E2DDD4", fontSize: 12 }} formatter={(v: number) => money(v, statement.data?.currency)} />
                    <Bar dataKey="billed" fill="#EFE4CC" radius={[4, 4, 0, 0]} barSize={16} />
                    <Line type="monotone" dataKey="paid" stroke="#1E7E4B" strokeWidth={2} dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>
            <div className="ap-chart-panel">
              <div className="ap-chart-head">
                <div><div className="panel-kicker">Mix</div><h2>Balance by status</h2></div>
              </div>
              {!statement.data.balance_by_status.length ? (
                <EmptyState title="Nothing open" />
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={statement.data.balance_by_status} dataKey="amount" nameKey="status" innerRadius={50} outerRadius={76} paddingAngle={2}>
                      {statement.data.balance_by_status.map((s, i) => <Cell key={s.status} fill={STATUS_COLORS[i % STATUS_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: 10, border: "0.5px solid #E2DDD4", fontSize: 12 }} formatter={(v: number, n) => [money(v, statement.data?.currency), n]} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <VendorControlsPanel vendorId={params.vendorId} />

          <section className="panel">
            <div className="panel-head">
              <div><div className="panel-kicker">History</div><h2>Recent invoices</h2></div>
            </div>
            {!statement.data.recent_invoices.length ? (
              <EmptyState title="No invoices from this vendor yet" />
            ) : (
              <div className="ap-table">
                <div className="ap-table-head" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr" }}>
                  <span>Invoice #</span><span>Amount</span><span>Status</span><span>Issued</span><span>Due</span>
                </div>
                {statement.data.recent_invoices.map((inv) => (
                  <Link key={inv.id} href={`/dashboard/document/${inv.document_id}`} className="ap-table-row" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr" }}>
                    <span className="ap-table-vendor">{inv.invoice_number || inv.id.slice(0, 8)}</span>
                    <span className="ap-table-amount">{money(inv.amount, inv.currency)}</span>
                    <span style={{ textTransform: "capitalize" }}>{inv.status.replaceAll("_", " ")}</span>
                    <span className="muted">{fmtDate(inv.issue_date)}</span>
                    <span className="muted">{fmtDate(inv.due_date)}</span>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </DashboardLayout>
  );
}

function ApMetric({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: React.ReactNode; tone?: "warn" | "danger" }) {
  return (
    <div className={`ap-metric-card${tone ? ` ${tone}` : ""}`}>
      <div className="ap-metric-icon">{icon}</div>
      <div>
        <div className="ap-metric-label">{label}</div>
        <div className="ap-metric-value">{value}</div>
      </div>
    </div>
  );
}

const REQUEST_STATUS_TONE: Record<VendorDocumentRequest["status"], string> = {
  pending: "warn",
  submitted: "warn",
  verified: "good",
  rejected: "danger",
  expired: "neutral",
};

function VendorControlsPanel({ vendorId }: { vendorId: string }) {
  const requests = useVendorDocumentRequests(vendorId);
  const requestDoc = useRequestVendorDocument();
  const verify = useVerifyBankChange();
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [portalLink, setPortalLink] = useState<string | null>(null);

  const w9Requests = requests.data?.filter((r) => r.request_type === "w9") ?? [];
  const bankRequests = requests.data?.filter((r) => r.request_type === "bank_verification") ?? [];

  const latestW9 = w9Requests[0];
  const latestBank = bankRequests[0];

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <div className="panel-kicker">Vendor controls</div>
          <h2>W-9 &amp; bank-change verification</h2>
          <p>
            A pending bank change or a missing W-9 blocks payment automatically — see the payment queue for any
            invoice this affects.
          </p>
        </div>
      </div>

      {portalLink && (
        <div className="soft-notice" style={{ marginBottom: 12 }}>
          Vendor portal link: <a href={portalLink} target="_blank" rel="noreferrer">{portalLink}</a>
        </div>
      )}
      {requests.isLoading ? (
        <PageLoading variant="cards" />
      ) : (
        <div className="vendor-controls-grid">
          <div className="vendor-control-card">
            <div className="vendor-control-card-head">
              <strong>W-9</strong>
              {latestW9 && <span className={`status-pill ${REQUEST_STATUS_TONE[latestW9.status]}`}>{latestW9.status}</span>}
            </div>
            {latestW9?.status === "submitted" ? (
              <p className="muted">Submitted — on file, no action needed.</p>
            ) : latestW9?.status === "pending" ? (
              <p className="muted">Waiting on the vendor to submit via their link.</p>
            ) : (
              <p className="muted">No W-9 on file for this vendor.</p>
            )}
            <button
              className="btn-secondary"
              disabled={requestDoc.isPending || latestW9?.status === "pending" || latestW9?.status === "submitted"}
              onClick={() => requestDoc.mutate(
                { vendorId, requestType: "w9" },
                { onSuccess: (created) => setPortalLink(`${window.location.origin}/vendor-portal/${created.token}`) },
              )}
            >
              {latestW9?.status === "submitted" ? "Request new W-9" : "Request W-9"}
            </button>
          </div>

          <div className="vendor-control-card">
            <div className="vendor-control-card-head">
              <strong>Bank verification</strong>
              {latestBank && <span className={`status-pill ${REQUEST_STATUS_TONE[latestBank.status]}`}>{latestBank.status}</span>}
            </div>
            {latestBank?.status === "submitted" ? (
              <p className="muted">Vendor submitted new banking details — payment stays blocked until you verify.</p>
            ) : latestBank?.status === "pending" ? (
              <p className="muted">Waiting on the vendor to submit via their link.</p>
            ) : (
              <p className="muted">No bank change pending.</p>
            )}

            {latestBank?.status === "submitted" && rejectingId !== latestBank.id && (
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn-secondary" disabled={verify.isPending} onClick={() => verify.mutate({ requestId: latestBank.id, approve: true })}>
                  Approve change
                </button>
                <button className="btn-danger-outline" onClick={() => setRejectingId(latestBank.id)}>
                  Reject
                </button>
              </div>
            )}

            {latestBank?.status === "submitted" && rejectingId === latestBank.id && (
              <div>
                <textarea
                  className="modal-textarea"
                  placeholder="Why is this bank change being rejected?"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  rows={2}
                />
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn-secondary" onClick={() => { setRejectingId(null); setRejectReason(""); }}>Cancel</button>
                  <button
                    className="btn-danger-outline"
                    disabled={!rejectReason.trim() || verify.isPending}
                    onClick={() =>
                      verify.mutate(
                        { requestId: latestBank.id, approve: false, reason: rejectReason.trim() },
                        { onSuccess: () => { setRejectingId(null); setRejectReason(""); } },
                      )
                    }
                  >
                    Confirm reject
                  </button>
                </div>
              </div>
            )}

            {(!latestBank || latestBank.status === "verified" || latestBank.status === "rejected" || latestBank.status === "expired") && (
              <button className="btn-secondary" disabled={requestDoc.isPending} onClick={() => requestDoc.mutate(
                { vendorId, requestType: "bank_verification" },
                { onSuccess: (created) => setPortalLink(`${window.location.origin}/vendor-portal/${created.token}`) },
              )}>
                Request bank verification
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
