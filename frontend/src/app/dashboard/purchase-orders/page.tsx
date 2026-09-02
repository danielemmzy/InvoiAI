"use client";
// Purchase orders — /dashboard/purchase-orders
// Built against BACKEND_INTEGRATION_AP_DASHBOARD.md §10 — the router this
// calls doesn't exist yet, the service and repository underneath it do.

import { useState } from "react";
import { Search, RotateCcw, FileStack } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError, EmptyState } from "@/components/ui/PageState";
import { usePurchaseOrders } from "@/hooks/useApprovalsInsightsPO";
import type { PurchaseOrderStatus } from "@/api/purchase-orders";

function money(n: number, currency = "USD") {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
  } catch {
    return `$${Math.round(n).toLocaleString()}`;
  }
}

function fmtDate(d: string | null) {
  if (!d) return "—";
  const date = new Date(d);
  return Number.isNaN(date.getTime()) ? d : date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

const STATUS_TONE: Record<PurchaseOrderStatus, string> = {
  open: "neutral",
  partially_matched: "warn",
  matched: "good",
};

const STATUS_LABEL: Record<PurchaseOrderStatus, string> = {
  open: "Open",
  partially_matched: "Partially matched",
  matched: "Matched",
};

export default function PurchaseOrdersPage() {
  const [search, setSearch] = useState("");
  const [isOpen, setIsOpen] = useState<string>("");
  const orders = usePurchaseOrders({ search: search || undefined, is_open: isOpen === "" ? undefined : isOpen === "true" });
  const hasFilters = !!search || isOpen !== "";

  return (
    <DashboardLayout>
      <div className="page-head">
        <div>
          <div className="eyebrow">Procurement</div>
          <h1 className="page-title">Purchase orders</h1>
          <p className="page-subtitle">Every PO you've issued, and how much of it has been matched to an invoice.</p>
        </div>
      </div>

      <div className="ap-filters">
        <div className="ap-filter-search">
          <Search size={14} />
          <input type="text" placeholder="Search PO number or vendor" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <select className="ap-filter-select" value={isOpen} onChange={(e) => setIsOpen(e.target.value)}>
          <option value="">All POs</option>
          <option value="true">Open only</option>
          <option value="false">Closed only</option>
        </select>
        <button type="button" className="ap-filter-reset" onClick={() => { setSearch(""); setIsOpen(""); }} disabled={!hasFilters}>
          <RotateCcw size={13} /> Reset
        </button>
      </div>

      <section className="panel">
        {orders.isLoading ? (
          <PageLoading variant="table" rows={7} />
        ) : orders.isError ? (
          <PageError title="Couldn't load purchase orders" onRetry={orders.refetch} />
        ) : !orders.data?.items.length ? (
          <EmptyState
            icon={FileStack}
            title={hasFilters ? "No purchase orders match" : "No purchase orders yet"}
            message={hasFilters ? "Try a different search or status." : "POs synced from QuickBooks or Xero, or created directly, will show up here."}
          />
        ) : (
          <div className="ap-table">
            <div className="ap-table-head" style={{ gridTemplateColumns: "1fr 1.3fr 1fr 1fr 1fr 1fr" }}>
              <span>PO number</span><span>Vendor</span><span>Amount</span><span>Matched</span><span>Status</span><span>Issued</span>
            </div>
            {orders.data.items.map((po) => (
              <div key={po.id} className="ap-table-row" style={{ gridTemplateColumns: "1fr 1.3fr 1fr 1fr 1fr 1fr", cursor: "default" }}>
                <span className="ap-table-vendor">{po.po_number}</span>
                <span>{po.vendor_name}</span>
                <span className="ap-table-amount">{money(po.amount, po.currency)}</span>
                <span className="muted">{money(po.matched_amount, po.currency)}</span>
                <span><span className={`status-pill ${STATUS_TONE[po.status]}`}>{STATUS_LABEL[po.status]}</span></span>
                <span className="muted">{fmtDate(po.issued_date)}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </DashboardLayout>
  );
}
