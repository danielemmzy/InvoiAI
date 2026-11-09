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
  Building2, FileStack, Wallet, ShieldCheck, CheckCircle2,
  ArrowRight, Upload, ArrowUpRight,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError } from "@/components/ui/PageState";
import { useAppStore } from "@/store/useAppStore";
import PersonalDashboardPage from "./personal/page";
import { useDocuments } from "@/hooks/useDocuments";
import { useWorkspaces } from "@/hooks/useWorkspaces";
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
  const recentDocs = documents.slice(0, 5);
  const usedPct = user?.usage ? Math.min((user.usage.used / user.usage.limit) * 100, 100) : 0;
  const businessWorkspaceCount = (workspaces.data ?? []).filter((w) => w.type === "business").length;
  const processingCount = documents.filter((d) => ["pending", "processing", "ocr_running", "ocr_complete", "analysis_running"].includes(d.status)).length;
  const reviewCount = documents.filter((d) => ["needs_review", "rejected"].includes(d.status)).length;

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="dash-page-header">
        <div className="section-label">Overview</div>
        <div className="dash-title serif">
          Good morning, {user?.email?.split("@")[0] || "there"}.
        </div>
        <div className="dash-subtitle">Your finance workspace.</div>
      </div>

      {/* Fast first paint: dashboard loads documents/workspaces only. Heavy AP/insight/approval screens are opened on demand. */}
      {docsLoading || workspaces.isLoading ? (
        <PageLoading variant="cards" cards={4} />
      ) : (
        <div className="ap-metric-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
          <OverviewMetric icon={<FileStack />} label="Documents" value={documents.length} hint="All uploaded documents in this workspace." />
          <OverviewMetric icon={<Building2 />} label="Workspaces" value={businessWorkspaceCount} hint="Business workspaces you can access." />
          <OverviewMetric icon={<CheckCircle2 />} label="Processing" value={processingCount} hint="Documents still being read or checked." />
          <OverviewMetric icon={<ShieldCheck />} label="Attention" value={reviewCount} hint="Documents that need a decision." tone={reviewCount ? "warn" : undefined} />
        </div>
      )}

      {/* Navigation cards are intentionally lightweight; each module fetches its own data when opened. */}
      <div className="overview-module-row">
        <Link href="/dashboard/approvals" className="overview-module-card ds-gloss" data-tooltip="Review and decide on routed invoices."><div className="overview-module-icon warn"><ShieldCheck size={16} /></div><div className="overview-module-label">Approvals</div><ArrowRight size={14} className="overview-module-arrow" /></Link>
        <Link href="/dashboard/insights" className="overview-module-card ds-gloss" data-tooltip="See exceptions and trends worth acting on."><div className="overview-module-icon"><CheckCircle2 size={16} /></div><div className="overview-module-label">Insights</div><ArrowRight size={14} className="overview-module-arrow" /></Link>
        <Link href="/dashboard/purchase-orders" className="overview-module-card ds-gloss" data-tooltip="Review purchase orders and matching evidence."><div className="overview-module-icon"><FileStack size={16} /></div><div className="overview-module-label">Purchase orders</div><ArrowRight size={14} className="overview-module-arrow" /></Link>
        <Link href="/dashboard/ap" className="overview-module-card ds-gloss" data-tooltip="Open the payable queue, balances, and exceptions."><div className="overview-module-icon danger"><ArrowUpRight size={16} /></div><div className="overview-module-label">Payables</div><ArrowRight size={14} className="overview-module-arrow" /></Link>
      </div>

      {/* Usage bar */}
      {/* /auth/me can return usage: {} — a real but empty object, which
          is truthy in JS. Checking a real field inside it instead of the
          object's own existence avoids rendering "undefined/undefined
          documents" when there's genuinely no usage data yet. */}
      {user?.usage?.limit != null && (
        <div className="card ds-data-surface" style={{ marginBottom: 24 }}>
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
            {!user.usage.limit_reached && user.plan === "free" && (
              <Link href="/dashboard/billing" className="upgrade-pill" data-tooltip="See plan limits and upgrade options." style={{ textDecoration: "none" }}>
                <div>
                  <div className="upgrade-label">Need more documents?</div>
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
        <div className="card ds-data-surface">
          <div className="card-header">
            <span className="card-title">Recent documents</span>
            <Link href="/dashboard/history" className="card-action">View all →</Link>
          </div>
          {docsLoading ? (
            <PageLoading variant="table" rows={4} />
          ) : recentDocs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title serif">No documents yet</div>
              <Link href="/dashboard/upload" className="btn-primary">Upload document</Link>
            </div>
          ) : (
            recentDocs.map((doc) => <DocumentRow key={doc.id} doc={doc} />)
          )}
        </div>

        {/* Right column */}
        <div>
          {/* Keep the first paint lightweight. Vendor/AP analytics are loaded inside their own modules. */}
          <div className="card ds-data-surface" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <span className="card-title">Document activity</span>
              <Link href="/dashboard/history" className="card-action">Open history →</Link>
            </div>
            <div style={{ padding: "8px 20px 18px" }}>
              <div className="kv-row"><span className="kv-key">Completed</span><span className="kv-val">{documents.filter((d) => ["done", "needs_review", "approved", "rejected"].includes(d.status)).length}</span></div>
              <div className="kv-row"><span className="kv-key">Processing</span><span className="kv-val">{processingCount}</span></div>
              <div className="kv-row"><span className="kv-key">Needs attention</span><span className="kv-val">{reviewCount}</span></div>
            </div>
          </div>

          {/* Upload CTA */}
          <Link href="/dashboard/upload" style={{ textDecoration: "none", display: "block" }}>
            <button className="upload-card">
              <div className="upload-card-icon"><Upload size={18} /></div>
              <div className="upload-card-title serif">Upload a document</div>
              <div className="upload-card-btn">Choose file <ArrowRight size={14} /></div>
            </button>
          </Link>
        </div>
      </div>
    </DashboardLayout>
  );
}

function OverviewMetric({
  icon, label, value, hint, tone,
}: { icon: React.ReactNode; label: string; value: React.ReactNode; hint: string; tone?: "warn" | "danger" }) {
  return (
    <div className={`ap-metric-card${tone ? ` ${tone}` : ""}`} data-tooltip={hint}>
      <div className="ap-metric-icon">{icon}</div>
      <div>
        <div className="ap-metric-label">{label}</div>
        <div className="ap-metric-value">{value}</div>
      </div>
    </div>
  );
}
