"use client";
// Dashboard Overview — /dashboard
//
// This used to be four generic document-count metrics and nothing else —
// no vendors, no invoices, no approvals, no insights, no purchase orders,
// no sense of how many workspaces this account runs. Every one of those
// already has a working hook elsewhere in the app; this page just needed
// to actually pull from them.

import Link from "next/link";
import {
  Building2, FileStack, Wallet, UserCheck, Sparkles, ShoppingCart,
  ArrowRight, Upload, ArrowUpRight,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError } from "@/components/ui/PageState";
import { useAppStore } from "@/store/useAppStore";
import PersonalDashboardPage from "./personal/page";
import { useDocuments } from "@/hooks/useDocuments";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { useAPSummary, useTopVendors } from "@/hooks/useAP";
import { usePendingApprovals, useInsights, usePurchaseOrders } from "@/hooks/useApprovalsInsightsPO";
import { usePlanCatalog } from "@/hooks/useBilling";
import DocumentRow from "@/components/documents/DocumentRow";

function money(n: number | undefined, currency = "USD") {
  if (n === undefined || n === null) return "—";
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
  } catch {
    return `$${Math.round(n).toLocaleString()}`;
  }
}

export default function DashboardPage() {
  const { user, activeWorkspace } = useAppStore();
  if (activeWorkspace?.type === "personal") return <PersonalDashboardPage />;

  const { documents, isLoading: docsLoading } = useDocuments();
  const workspaces = useWorkspaces();
  const summary = useAPSummary();
  const topVendors = useTopVendors();
  const approvals = usePendingApprovals();
  const insights = useInsights();
  const purchaseOrders = usePurchaseOrders({ is_open: true, limit: 1 });
  const plans = usePlanCatalog();

  const recentDocs = documents.slice(0, 5);
  const usedPct = user?.usage ? Math.min((user.usage.used / user.usage.limit) * 100, 100) : 0;
  const businessWorkspaceCount = (workspaces.data ?? []).filter((w) => w.type === "business").length;
  const currentPlanEntry = plans.data?.find((p) => p.id === (user?.plan || "free"));
  const nextPlanEntry = plans.data?.find((p) => p.id === "starter");
  const activeInsightCount = (insights.data ?? []).filter((i) => !i.is_dismissed).length;

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="dash-page-header">
        <div className="section-label">§00 Console / Overview</div>
        <div className="dash-title serif">
          Good morning, {user?.email?.split("@")[0] || "there"}.
        </div>
        <div className="dash-subtitle">
          Everything across accounts payable, at a glance.
        </div>
      </div>

      {/* Top-level metrics — documents, vendors, invoices, workspaces */}
      {summary.isLoading || workspaces.isLoading ? (
        <PageLoading variant="cards" cards={6} />
      ) : summary.isError ? (
        <PageError title="Couldn't load your totals" onRetry={summary.refetch} />
      ) : (
        <div className="ap-metric-grid" style={{ gridTemplateColumns: "repeat(6, 1fr)" }}>
          <OverviewMetric icon={<FileStack />} label="Documents used" value={user?.usage?.used ?? 0} sub={`${user?.usage?.remaining ?? 0} left this month`} />
          <OverviewMetric icon={<Building2 />} label="Organizations" value={businessWorkspaceCount} sub={businessWorkspaceCount === 1 ? "business workspace" : "business workspaces"} />
          <OverviewMetric icon={<Building2 />} label="Vendors" value={summary.data?.total_vendors ?? 0} sub={`${summary.data?.open_vendors ?? 0} with an open balance`} />
          <OverviewMetric icon={<FileStack />} label="Invoices" value={summary.data?.total_invoices ?? 0} sub={`${summary.data?.open_invoices ?? 0} open`} />
          <OverviewMetric icon={<Wallet />} label="Billed / open" value={money(summary.data?.total_amount, summary.data?.currency)} sub={money(summary.data?.open_amount, summary.data?.currency) + " open"} tone={summary.data?.overdue_amount ? "danger" : undefined} />
          <OverviewMetric icon={<UserCheck />} label="Awaiting you" value={approvals.data?.length ?? 0} sub="pending approvals" tone={approvals.data?.length ? "warn" : undefined} />
        </div>
      )}

      {/* Module status row — approvals, insights, purchase orders, at a glance */}
      <div className="overview-module-row">
        <Link href="/dashboard/approvals" className="overview-module-card">
          <div className="overview-module-icon warn"><UserCheck size={16} /></div>
          <div>
            <div className="overview-module-value">{approvals.isLoading ? "—" : approvals.data?.length ?? 0}</div>
            <div className="overview-module-label">Pending approvals</div>
          </div>
          <ArrowRight size={14} className="overview-module-arrow" />
        </Link>
        <Link href="/dashboard/insights" className="overview-module-card">
          <div className="overview-module-icon"><Sparkles size={16} /></div>
          <div>
            <div className="overview-module-value">{insights.isLoading ? "—" : activeInsightCount}</div>
            <div className="overview-module-label">Active insights</div>
          </div>
          <ArrowRight size={14} className="overview-module-arrow" />
        </Link>
        <Link href="/dashboard/purchase-orders" className="overview-module-card">
          <div className="overview-module-icon"><ShoppingCart size={16} /></div>
          <div>
            <div className="overview-module-value">{purchaseOrders.isLoading ? "—" : purchaseOrders.data?.total ?? 0}</div>
            <div className="overview-module-label">Open purchase orders</div>
          </div>
          <ArrowRight size={14} className="overview-module-arrow" />
        </Link>
        <Link href="/dashboard/ap/aging" className="overview-module-card">
          <div className="overview-module-icon danger"><ArrowUpRight size={16} /></div>
          <div>
            <div className="overview-module-value">{summary.isLoading ? "—" : money(summary.data?.overdue_amount, summary.data?.currency)}</div>
            <div className="overview-module-label">Overdue balance</div>
          </div>
          <ArrowRight size={14} className="overview-module-arrow" />
        </Link>
      </div>

      {/* Usage bar */}
      {/* /auth/me can return usage: {} — a real but empty object, which
          is truthy in JS. Checking a real field inside it instead of the
          object's own existence avoids rendering "undefined/undefined
          documents" when there's genuinely no usage data yet. */}
      {user?.usage?.limit != null && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <span className="card-title">Monthly usage</span>
            <span style={{ fontSize: 12, color: "#6B6860" }}>
              {user.usage.used} / {user.usage.limit} documents
            </span>
          </div>
          <div className="usage-card">
            <div className="usage-bar-wrap">
              <div
                className={`usage-bar${user.usage.limit_reached ? " danger" : ""}`}
                style={{ width: `${usedPct}%` }}
              />
            </div>
            <div className="usage-counts">
              <span>{user.usage.used} used</span>
              <span>{user.usage.limit} limit</span>
            </div>
            {user.usage.limit_reached && (
              <div style={{ marginTop: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: "#E57373" }}>Monthly limit reached</span>
                <Link href="/dashboard/billing" className="btn-amber" style={{ padding: "6px 14px", fontSize: 12 }}>
                  Upgrade plan →
                </Link>
              </div>
            )}
            {!user.usage.limit_reached && user.plan === "free" && nextPlanEntry && (
              <Link href="/dashboard/billing" className="upgrade-pill" style={{ textDecoration: "none" }}>
                <div>
                  <div className="upgrade-label">Upgrade to {nextPlanEntry.display_name}</div>
                  <div className="upgrade-sub">
                    {typeof nextPlanEntry.monthly_documents === "number" ? `${nextPlanEntry.monthly_documents} docs` : "Unlimited docs"} · ${nextPlanEntry.price_monthly}/month
                  </div>
                </div>
                <span className="upgrade-arrow">→</span>
              </Link>
            )}
          </div>
        </div>
      )}

      {/* Main grid */}
      <div className="dash-grid">
        {/* Recent documents */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Recent documents</span>
            <Link href="/dashboard/history" className="card-action">View all →</Link>
          </div>
          {docsLoading ? (
            <PageLoading variant="table" rows={4} />
          ) : recentDocs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📄</div>
              <div className="empty-title serif">No documents yet</div>
              <div className="empty-desc">Upload your first invoice to get started.</div>
              <Link href="/dashboard/upload" className="btn-primary">Upload document</Link>
            </div>
          ) : (
            recentDocs.map((doc) => <DocumentRow key={doc.id} doc={doc} />)
          )}
        </div>

        {/* Right column */}
        <div>
          {/* Top vendors mini-list */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <span className="card-title">Top vendors</span>
              <Link href="/dashboard/vendors" className="card-action">All vendors →</Link>
            </div>
            {topVendors.isLoading ? (
              <PageLoading variant="table" rows={3} />
            ) : !topVendors.data?.length ? (
              <div className="empty-state" style={{ padding: "28px 20px" }}>
                <div className="empty-desc">No vendor balances yet.</div>
              </div>
            ) : (
              <div style={{ padding: "6px 20px 14px" }}>
                {topVendors.data.slice(0, 4).map((v) => (
                  <div key={v.vendor_id} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "0.5px solid #EBE6DC", fontSize: 13 }}>
                    <span>{v.vendor_name}</span>
                    <b>{money(v.current_balance, v.currency)}</b>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Upload CTA */}
          <Link href="/dashboard/upload" style={{ textDecoration: "none", display: "block" }}>
            <button className="upload-card">
              <div className="upload-card-icon"><Upload size={18} /></div>
              <div className="upload-card-title serif">Upload a document</div>
              <div className="upload-card-sub">
                PDF, image, or scanned file.<br />Results in under 5 seconds.
              </div>
              <div className="upload-card-btn">Choose file →</div>
            </button>
          </Link>
        </div>
      </div>
    </DashboardLayout>
  );
}

function OverviewMetric({
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
