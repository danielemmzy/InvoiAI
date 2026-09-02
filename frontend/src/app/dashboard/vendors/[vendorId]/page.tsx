"use client";
// Vendor statement — /dashboard/vendors/[vendorId]

import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ShieldAlert, ShieldCheck, Clock3, Wallet, CreditCard, FileStack } from "lucide-react";
import {
  ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell,
} from "recharts";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError, EmptyState } from "@/components/ui/PageState";
import { useVendorStatement } from "@/hooks/useAP";

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
