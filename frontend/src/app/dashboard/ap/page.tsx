"use client";
// AP control center — /dashboard/ap
// Totals, trend charts, top vendors by risk, and the working invoice queue.
// See BACKEND_INTEGRATION_AP_DASHBOARD.md for the endpoints this reads.

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowRight, Building2, FileStack, Wallet,
  Clock3, X, Search, RotateCcw, ChevronRight, ShieldAlert, ShieldCheck, ExternalLink,
  CalendarDays, Tag, CheckCircle2, Loader2,
} from "lucide-react";
import {
  ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, LineChart,
} from "recharts";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError, EmptyState } from "@/components/ui/PageState";
import { useAPSummary, useAPInvoices, useTopVendors, useApproveCodings } from "@/hooks/useAP";
import type { APDashboardFilters, APInvoiceRow, InvoiceStatusFilter } from "@/api/ap";

const CHART_TEAL = "#1E7E4B";
const CHART_GOLD = "#C8922A";
const CHART_INK = "#1A1916";
const CHART_MUTED = "#AAA8A0";
const PIE_COLORS = ["#1A1916", "#C8922A", "#8B6420", "#D8CFBB", "#6B6860"];

const STATUS_OPTIONS: { value: InvoiceStatusFilter | ""; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "awaiting_approval", label: "Awaiting approval" },
  { value: "approved", label: "Approved" },
  { value: "match_exception", label: "Match exception" },
  { value: "coding_exception", label: "Coding exception" },
  { value: "payment_ready", label: "Payment ready" },
  { value: "overdue", label: "Overdue" },
  { value: "paid", label: "Paid" },
];

const PRIORITY_OPTIONS = [
  { value: "", label: "Any priority" },
  { value: "urgent", label: "Urgent" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

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
  if (Number.isNaN(date.getTime())) return d;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

const emptyFilters: APDashboardFilters = {};

export default function APDashboardPage() {
  const [filters, setFilters] = useState<APDashboardFilters>(emptyFilters);
  const [pendingSearch, setPendingSearch] = useState("");
  const [previewId, setPreviewId] = useState<string | null>(null);

  const summary = useAPSummary(filters);
  const invoices = useAPInvoices({ ...filters, limit: 25 });
  const topVendors = useTopVendors(filters);

  const hasFilters = Object.values(filters).some((v) => !!v);

  function updateFilter<K extends keyof APDashboardFilters>(key: K, value: APDashboardFilters[K]) {
    setFilters((f) => ({ ...f, [key]: value || undefined }));
  }

  function resetFilters() {
    setFilters(emptyFilters);
    setPendingSearch("");
  }

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    updateFilter("search", pendingSearch.trim() || undefined);
  }

  const previewInvoice = useMemo(
    () => invoices.data?.items.find((i) => i.id === previewId) || null,
    [invoices.data, previewId]
  );

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="page-head">
        <div>
          <div className="eyebrow">Accounts payable</div>
          <h1 className="page-title">AP control center</h1>
          <p className="page-subtitle">
            Every vendor balance, every open invoice, and what needs a decision today,
            all in one place.
          </p>
        </div>
        <div className="ap-subnav">
          <Link href="/dashboard/ap" className="ap-subnav-item active">Overview</Link>
          <Link href="/dashboard/ap/aging" className="ap-subnav-item">Aging analysis</Link>
          <Link href="/dashboard/ap/exceptions" className="ap-subnav-item">Exceptions</Link>
        </div>
      </div>

      {/* Filters */}
      <div className="ap-filters">
        <form className="ap-filter-search" onSubmit={submitSearch}>
          <Search size={14} />
          <input
            type="text"
            placeholder="Search vendor or invoice number"
            value={pendingSearch}
            onChange={(e) => setPendingSearch(e.target.value)}
          />
        </form>
        <div className="ap-filter-field">
          <CalendarDays size={13} />
          <input type="date" value={filters.date_from ?? ""} onChange={(e) => updateFilter("date_from", e.target.value)} aria-label="From date" />
        </div>
        <span className="ap-filter-sep">to</span>
        <div className="ap-filter-field">
          <CalendarDays size={13} />
          <input type="date" value={filters.date_to ?? ""} onChange={(e) => updateFilter("date_to", e.target.value)} aria-label="To date" />
        </div>
        <select className="ap-filter-select" value={filters.status ?? ""} onChange={(e) => updateFilter("status", e.target.value as InvoiceStatusFilter)}>
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select className="ap-filter-select" value={filters.priority ?? ""} onChange={(e) => updateFilter("priority", e.target.value as APDashboardFilters["priority"])}>
          {PRIORITY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select className="ap-filter-select" value={filters.currency ?? ""} onChange={(e) => updateFilter("currency", e.target.value)}>
          <option value="">All currencies</option>
          <option value="USD">USD</option>
          <option value="EUR">EUR</option>
          <option value="GBP">GBP</option>
          <option value="NGN">NGN</option>
        </select>
        <button type="button" className="ap-filter-reset" onClick={resetFilters} disabled={!hasFilters}>
          <RotateCcw size={13} /> Reset
        </button>
      </div>

      {/* Totals */}
      {summary.isLoading ? (
        <PageLoading variant="cards" cards={6} />
      ) : summary.isError ? (
        <PageError title="Couldn't load AP totals" onRetry={summary.refetch} />
      ) : (
        <div className="ap-metric-grid">
          <ApMetric icon={<Building2 />} label="Total vendors" value={summary.data?.total_vendors ?? 0} />
          <ApMetric icon={<Building2 />} label="Open vendors" value={summary.data?.open_vendors ?? 0} tone="warn" />
          <ApMetric icon={<FileStack />} label="Total invoices" value={summary.data?.total_invoices ?? 0} />
          <ApMetric icon={<FileStack />} label="Open invoices" value={summary.data?.open_invoices ?? 0} tone="warn" />
          <ApMetric icon={<Wallet />} label="Total billed / paid" value={money(summary.data?.total_amount, summary.data?.currency)} sub={`${money(summary.data?.total_paid, summary.data?.currency)} paid`} />
          <ApMetric icon={<Clock3 />} label="Open amount" value={money(summary.data?.open_amount, summary.data?.currency)} sub={summary.data?.overdue_amount ? `${money(summary.data.overdue_amount, summary.data.currency)} overdue` : undefined} tone={summary.data?.overdue_amount ? "danger" : undefined} />
        </div>
      )}

      {/* Charts */}
      <div className="ap-chart-grid">
        <div className="ap-chart-panel wide">
          <div className="ap-chart-head">
            <div>
              <div className="panel-kicker">Trend</div>
              <h2>Payables by month</h2>
            </div>
          </div>
          {summary.isLoading ? (
            <PageLoading variant="chart" />
          ) : summary.isError ? (
            <PageError compact onRetry={summary.refetch} />
          ) : !summary.data?.payables_by_month?.length ? (
            <EmptyState title="No billing history yet" message="Payables by month will chart itself in as invoices come through." />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={summary.data.payables_by_month} margin={{ left: -12, right: 8, top: 8 }}>
                <CartesianGrid stroke="#E2DDD4" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: CHART_MUTED }} axisLine={{ stroke: "#E2DDD4" }} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: CHART_MUTED }} axisLine={false} tickLine={false} width={54} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
                <Tooltip contentStyle={{ borderRadius: 10, border: "0.5px solid #E2DDD4", fontSize: 12 }} formatter={(v: number) => money(v)} />
                <Bar dataKey="billed" name="Billed" fill="#EFE4CC" radius={[4, 4, 0, 0]} barSize={18} />
                <Line type="monotone" dataKey="paid" name="Paid" stroke={CHART_TEAL} strokeWidth={2} dot={{ r: 3, fill: CHART_TEAL }} />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="ap-chart-panel">
          <div className="ap-chart-head">
            <div>
              <div className="panel-kicker">Efficiency</div>
              <h2>Payable turnover</h2>
            </div>
            <div className="ap-turnover-value serif">{summary.data?.payable_turnover_days ?? "—"}<span> days</span></div>
          </div>
          {summary.isLoading ? (
            <PageLoading variant="chart" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={summary.data?.payable_turnover_trend ?? []} margin={{ left: -20, right: 8, top: 8 }}>
                <CartesianGrid stroke="#E2DDD4" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: CHART_MUTED }} axisLine={{ stroke: "#E2DDD4" }} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: CHART_MUTED }} axisLine={false} tickLine={false} width={30} />
                <Tooltip contentStyle={{ borderRadius: 10, border: "0.5px solid #E2DDD4", fontSize: 12 }} />
                <Line type="monotone" dataKey="days" stroke={CHART_GOLD} strokeWidth={2} dot={{ r: 3, fill: CHART_GOLD }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="ap-chart-panel">
          <div className="ap-chart-head">
            <div>
              <div className="panel-kicker">Exposure</div>
              <h2>Payables by currency</h2>
            </div>
          </div>
          {summary.isLoading ? (
            <PageLoading variant="chart" />
          ) : !summary.data?.by_currency?.length ? (
            <EmptyState title="Single currency" message="Everything so far is in one currency." />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={summary.data.by_currency} dataKey="amount" nameKey="currency" innerRadius={52} outerRadius={78} paddingAngle={2}>
                  {summary.data.by_currency.map((entry, i) => (
                    <Cell key={entry.currency} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 10, border: "0.5px solid #E2DDD4", fontSize: 12 }} formatter={(v: number, n) => [money(v), n]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Top vendors */}
      <section className="panel ap-vendor-panel">
        <div className="panel-head">
          <div>
            <div className="panel-kicker">Concentration</div>
            <h2>Top vendors by balance</h2>
            <p>Current and overdue balance, with a live risk read for each.</p>
          </div>
          <Link href="/dashboard/vendors" className="text-link">All vendors <ArrowRight size={14} /></Link>
        </div>
        {topVendors.isLoading ? (
          <PageLoading variant="table" rows={5} />
        ) : topVendors.isError ? (
          <PageError compact onRetry={topVendors.refetch} />
        ) : !topVendors.data?.length ? (
          <EmptyState title="No vendor balances yet" message="Top vendors will rank themselves here as invoices come in." />
        ) : (
          <div className="top-vendor-list">
            {topVendors.data.map((v) => (
              <Link key={v.vendor_id} href={`/dashboard/vendors/${v.vendor_id}`} className="top-vendor-row">
                <div className="top-vendor-name">{v.vendor_name}</div>
                <div className="top-vendor-balances">
                  <span>{money(v.current_balance, v.currency)} current</span>
                  {v.overdue_balance > 0 && <span className="danger">{money(v.overdue_balance, v.currency)} overdue</span>}
                </div>
                <RiskBar score={v.risk_score} level={v.risk_level} />
                <ChevronRight size={15} className="top-vendor-chevron" />
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Unpaid invoices table */}
      <section className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-kicker">Queue</div>
            <h2>Open invoices</h2>
            <p>Click any row for a quick preview before you approve it.</p>
          </div>
          <div className="muted">{invoices.data?.total ?? 0} matching</div>
        </div>

        {invoices.isLoading ? (
          <PageLoading variant="table" rows={8} />
        ) : invoices.isError ? (
          <PageError onRetry={invoices.refetch} />
        ) : !invoices.data?.items.length ? (
          <EmptyState
            icon={CheckCircle2}
            title={hasFilters ? "No invoices match these filters" : "Nothing open right now"}
            message={hasFilters ? "Try widening the date range or clearing a filter." : "Every invoice is settled. New ones will land here as they come in."}
            action={hasFilters ? <button className="btn-secondary" onClick={resetFilters}><RotateCcw size={13} /> Reset filters</button> : undefined}
          />
        ) : (
          <div className="ap-table">
            <div className="ap-table-head">
              <span>Vendor</span>
              <span>Amount</span>
              <span>Status</span>
              <span>Priority</span>
              <span>Tags</span>
              <span>Issued</span>
              <span>Due</span>
            </div>
            {invoices.data.items.map((row) => (
              <button type="button" key={row.id} className="ap-table-row" onClick={() => setPreviewId(row.id)}>
                <span className="ap-table-vendor">{row.vendor_name}</span>
                <span className="ap-table-amount">{money(row.amount, row.currency)}</span>
                <span><StatusPill status={row.status} /></span>
                <span><PriorityPill priority={row.priority} /></span>
                <span className="ap-table-tags">
                  {row.tags.slice(0, 2).map((t) => <span key={t} className="ap-tag"><Tag size={9} />{t}</span>)}
                  {row.tags.length > 2 && <span className="ap-tag muted">+{row.tags.length - 2}</span>}
                </span>
                <span className="muted">{fmtDate(row.issue_date)}</span>
                <span className="muted">{fmtDate(row.due_date)}</span>
              </button>
            ))}
          </div>
        )}
      </section>

      {previewInvoice && <InvoicePreviewDrawer invoice={previewInvoice} onClose={() => setPreviewId(null)} />}
    </DashboardLayout>
  );
}

/* ── Building blocks ────────────────────────────────────────── */

function ApMetric({
  icon, label, value, sub, tone,
}: { icon: React.ReactNode; label: string; value: React.ReactNode; sub?: string; tone?: "warn" | "danger" }) {
  return (
    <div className={`ap-metric-card${tone ? ` ${tone}` : ""}`}>
      <div className="ap-metric-icon">{icon}</div>
      <div>
        <div className="ap-metric-label">{label}</div>
        <div className="ap-metric-value">{value}</div>
        {sub && <div className="ap-metric-sub">{sub}</div>}
      </div>
    </div>
  );
}

function RiskBar({ score, level }: { score: number; level: "low" | "medium" | "high" }) {
  const tone = level === "high" ? "danger" : level === "medium" ? "warn" : "good";
  return (
    <div className="risk-bar-wrap" title={`Risk score ${score}/100`}>
      <div className="risk-bar-track">
        <div className={`risk-bar-fill ${tone}`} style={{ width: `${Math.min(100, Math.max(4, score))}%` }} />
      </div>
      <span className={`risk-bar-label ${tone}`}>{level}</span>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, { label: string; tone: string }> = {
    awaiting_approval: { label: "Awaiting approval", tone: "warn" },
    approved: { label: "Approved", tone: "good" },
    match_exception: { label: "Match exception", tone: "danger" },
    coding_exception: { label: "Coding exception", tone: "danger" },
    payment_ready: { label: "Payment ready", tone: "good" },
    overdue: { label: "Overdue", tone: "danger" },
    paid: { label: "Paid", tone: "neutral" },
    rejected: { label: "Rejected", tone: "danger" },
  };
  const m = map[status] || { label: status.replaceAll("_", " "), tone: "neutral" };
  return <span className={`status-pill ${m.tone}`}>{m.label}</span>;
}

function PriorityPill({ priority }: { priority: string }) {
  return <span className={`priority-pill ${priority}`}>{priority}</span>;
}

function InvoicePreviewDrawer({ invoice, onClose }: { invoice: APInvoiceRow; onClose: () => void }) {
  const approve = useApproveCodings();
  const canApprove = invoice.status === "awaiting_approval" || invoice.status === "coding_exception";

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer-panel" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Invoice preview">
        <div className="drawer-head">
          <div>
            <div className="panel-kicker">Invoice preview</div>
            <h2 className="serif">{invoice.vendor_name}</h2>
          </div>
          <button className="drawer-close" onClick={onClose} aria-label="Close preview"><X size={18} /></button>
        </div>

        <div className="drawer-amount">{money(invoice.amount, invoice.currency)}</div>

        <div className="drawer-grid">
          <div><span className="muted">Invoice #</span><strong>{invoice.invoice_number || "—"}</strong></div>
          <div><span className="muted">Status</span><StatusPill status={invoice.status} /></div>
          <div><span className="muted">Priority</span><PriorityPill priority={invoice.priority} /></div>
          <div><span className="muted">Health score</span><strong>{invoice.health_score ?? "—"}{invoice.health_score ? "/100" : ""}</strong></div>
          <div><span className="muted">Issued</span><strong>{fmtDate(invoice.issue_date)}</strong></div>
          <div><span className="muted">Due</span><strong>{fmtDate(invoice.due_date)}</strong></div>
        </div>

        {invoice.tags.length > 0 && (
          <div className="drawer-tags">
            {invoice.tags.map((t) => <span key={t} className="ap-tag"><Tag size={10} />{t}</span>)}
          </div>
        )}

        {invoice.risk_level && (
          <div className={`drawer-risk-note ${invoice.risk_level}`}>
            {invoice.risk_level === "low" ? <ShieldCheck size={15} /> : <ShieldAlert size={15} />}
            {invoice.risk_level === "low" ? "Low risk. Verification passed cleanly." : `${invoice.risk_level === "high" ? "High" : "Medium"} risk. Worth a look before approving.`}
          </div>
        )}

        <div className="drawer-actions">
          <Link href={`/dashboard/document/${invoice.document_id}`} className="btn-secondary">
            Full document <ExternalLink size={13} />
          </Link>
          {canApprove && (
            <button
              className="btn-primary"
              onClick={() => approve.mutate(invoice.document_id, { onSuccess: onClose })}
              disabled={approve.isPending}
            >
              {approve.isPending ? <Loader2 size={14} className="spin" /> : <CheckCircle2 size={14} />}
              Approve
            </button>
          )}
        </div>
      </aside>
    </div>
  );
}
