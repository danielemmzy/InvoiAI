"use client";
// AP aging analysis — /dashboard/ap/aging

import { useState } from "react";
import Link from "next/link";
import { RotateCcw, CalendarDays } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from "recharts";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError, EmptyState } from "@/components/ui/PageState";
import { useAPAging } from "@/hooks/useAP";
import type { APDashboardFilters } from "@/api/ap";

const BUCKET_COLORS: Record<string, string> = {
  current: "#1E7E4B",
  "1_30": "#C8922A",
  "31_60": "#D8A13A",
  "61_90": "#C97A3F",
  "90_plus": "#C0392B",
};

function money(n: number, currency = "USD") {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
  } catch {
    return `$${Math.round(n).toLocaleString()}`;
  }
}

export default function AgingAnalysisPage() {
  const [filters, setFilters] = useState<APDashboardFilters>({});
  const aging = useAPAging(filters);
  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <DashboardLayout>
      <div className="page-head">
        <div>
          <div className="eyebrow">Accounts payable</div>
          <h1 className="page-title">Aging analysis</h1>
          <p className="page-subtitle">
            How much is owed, and how long it has been owed, broken down by vendor.
          </p>
        </div>
        <div className="ap-subnav">
          <Link href="/dashboard/ap" className="ap-subnav-item">Overview</Link>
          <Link href="/dashboard/ap/aging" className="ap-subnav-item active">Aging analysis</Link>
          <Link href="/dashboard/ap/exceptions" className="ap-subnav-item">Exceptions</Link>
        </div>
      </div>

      <div className="ap-filters">
        <div className="ap-filter-field">
          <CalendarDays size={13} />
          <input type="date" value={filters.date_from ?? ""} onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value || undefined }))} aria-label="As of from" />
        </div>
        <span className="ap-filter-sep">as of</span>
        <div className="ap-filter-field">
          <CalendarDays size={13} />
          <input type="date" value={filters.date_to ?? ""} onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value || undefined }))} aria-label="As of to" />
        </div>
        <button type="button" className="ap-filter-reset" onClick={() => setFilters({})} disabled={!hasFilters}>
          <RotateCcw size={13} /> Reset
        </button>
      </div>

      <div className="ap-chart-panel" style={{ marginBottom: 22 }}>
        <div className="ap-chart-head">
          <div>
            <div className="panel-kicker">Buckets</div>
            <h2>Open balance by age</h2>
          </div>
        </div>
        {aging.isLoading ? (
          <PageLoading variant="chart" />
        ) : aging.isError ? (
          <PageError onRetry={aging.refetch} />
        ) : !aging.data?.buckets?.length ? (
          <EmptyState title="Nothing outstanding" message="Every invoice is current. No aging to analyze." />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={aging.data.buckets} margin={{ left: -8, right: 8, top: 8 }}>
              <CartesianGrid stroke="#E2DDD4" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#AAA8A0" }} axisLine={{ stroke: "#E2DDD4" }} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#AAA8A0" }} axisLine={false} tickLine={false} width={54} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
              <Tooltip contentStyle={{ borderRadius: 10, border: "0.5px solid #E2DDD4", fontSize: 12 }} formatter={(v: number) => money(v, aging.data?.currency)} />
              <Bar dataKey="amount" radius={[6, 6, 0, 0]} barSize={54}>
                {aging.data.buckets.map((b) => <Cell key={b.bucket} fill={BUCKET_COLORS[b.bucket] || "#C8922A"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <section className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-kicker">By vendor</div>
            <h2>Aging schedule</h2>
            <p>Each vendor's open balance, split across the same age buckets.</p>
          </div>
        </div>
        {aging.isLoading ? (
          <PageLoading variant="table" rows={7} />
        ) : aging.isError ? (
          <PageError compact onRetry={aging.refetch} />
        ) : !aging.data?.rows?.length ? (
          <EmptyState title="No open vendor balances" />
        ) : (
          <div className="ap-table">
            <div className="ap-table-head" style={{ gridTemplateColumns: "1.4fr 1fr 1fr 1fr 1fr 1fr" }}>
              <span>Vendor</span>
              <span>Current</span>
              <span>1&ndash;30</span>
              <span>31&ndash;60</span>
              <span>61&ndash;90</span>
              <span>90+</span>
            </div>
            {aging.data.rows.map((r) => (
              <Link key={r.vendor_id} href={`/dashboard/vendors/${r.vendor_id}`} className="ap-table-row" style={{ gridTemplateColumns: "1.4fr 1fr 1fr 1fr 1fr 1fr" }}>
                <span className="ap-table-vendor">{r.vendor_name}</span>
                <span>{money(r.current, aging.data?.currency)}</span>
                <span>{money(r.d1_30, aging.data?.currency)}</span>
                <span>{money(r.d31_60, aging.data?.currency)}</span>
                <span>{money(r.d61_90, aging.data?.currency)}</span>
                <span style={{ color: r.d90_plus > 0 ? "#C0392B" : undefined, fontWeight: r.d90_plus > 0 ? 600 : undefined }}>
                  {money(r.d90_plus, aging.data?.currency)}
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </DashboardLayout>
  );
}
