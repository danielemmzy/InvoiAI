"use client";
// Vendors — /dashboard/vendors

import { useState } from "react";
import Link from "next/link";
import { Search, RotateCcw, ShieldAlert, ChevronRight, Star, Ban } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError, EmptyState } from "@/components/ui/PageState";
import { useVendorsList } from "@/hooks/useAP";

function money(n: number, currency = "USD") {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
  } catch {
    return `$${Math.round(n).toLocaleString()}`;
  }
}

export default function VendorsPage() {
  const [search, setSearch] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const vendors = useVendorsList({ search: search || undefined, risk_level: riskLevel || undefined });
  const hasFilters = !!search || !!riskLevel;

  return (
    <DashboardLayout>
      <div className="page-head">
        <div>
          <div className="eyebrow">Accounts payable</div>
          <h1 className="page-title">Vendors</h1>
          <p className="page-subtitle">Every vendor you've ever paid, with a live risk read and their open balance.</p>
        </div>
      </div>

      <div className="ap-filters">
        <div className="ap-filter-search">
          <Search size={14} />
          <input type="text" placeholder="Search vendors" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <select className="ap-filter-select" value={riskLevel} onChange={(e) => setRiskLevel(e.target.value)}>
          <option value="">Any risk level</option>
          <option value="low">Low risk</option>
          <option value="medium">Medium risk</option>
          <option value="high">High risk</option>
        </select>
        <button type="button" className="ap-filter-reset" onClick={() => { setSearch(""); setRiskLevel(""); }} disabled={!hasFilters}>
          <RotateCcw size={13} /> Reset
        </button>
      </div>

      <section className="panel">
        {vendors.isLoading ? (
          <PageLoading variant="table" rows={8} />
        ) : vendors.isError ? (
          <PageError onRetry={vendors.refetch} />
        ) : !vendors.data?.length ? (
          <EmptyState
            icon={ShieldAlert}
            title={hasFilters ? "No vendors match" : "No vendors yet"}
            message={hasFilters ? "Try a different search or risk level." : "Vendors appear automatically the first time you receive an invoice from them."}
          />
        ) : (
          <div className="ap-table">
            <div className="ap-table-head" style={{ gridTemplateColumns: "1.6fr 1fr 1fr 1fr 40px" }}>
              <span>Vendor</span>
              <span>Total spend</span>
              <span>Open balance</span>
              <span>Risk</span>
              <span />
            </div>
            {vendors.data.map((v) => (
              <Link key={v.id} href={`/dashboard/vendors/${v.id}`} className="ap-table-row" style={{ gridTemplateColumns: "1.6fr 1fr 1fr 1fr 40px" }}>
                <span className="ap-table-vendor" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  {v.name}
                  {v.is_preferred && <Star size={12} color="#C8922A" fill="#C8922A" />}
                  {v.is_blocked && <Ban size={12} color="#C0392B" />}
                </span>
                <span>{money(v.total_spend, v.currency)}</span>
                <span>{money(v.open_balance, v.currency)}</span>
                <span>
                  <div className="risk-bar-wrap">
                    <div className="risk-bar-track">
                      <div className={`risk-bar-fill ${v.risk_level === "high" ? "danger" : v.risk_level === "medium" ? "warn" : "good"}`} style={{ width: `${Math.max(4, v.risk_score)}%` }} />
                    </div>
                    <span className={`risk-bar-label ${v.risk_level === "high" ? "danger" : v.risk_level === "medium" ? "warn" : "good"}`}>{v.risk_level}</span>
                  </div>
                </span>
                <ChevronRight size={15} color="#AAA8A0" />
              </Link>
            ))}
          </div>
        )}
      </section>
    </DashboardLayout>
  );
}
