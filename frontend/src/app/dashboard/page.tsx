"use client";
// Dashboard Overview — /dashboard

import Link from "next/link";
import { Upload } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useAppStore } from "@/store/useAppStore";
import { useDocuments } from "@/hooks/useDocuments";
import DocumentRow from "@/components/documents/DocumentRow";

export default function DashboardPage() {
  const { user } = useAppStore();
  const { documents, isLoading } = useDocuments();
  const recentDocs = documents.slice(0, 5);
  const usedPct = user?.usage
    ? Math.min((user.usage.used / user.usage.limit) * 100, 100)
    : 0;

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="dash-page-header">
        <div className="section-label">§00 Console / Overview</div>
        <div className="dash-title serif">
          Good morning, {user?.email?.split("@")[0] || "there"}.
        </div>
        <div className="dash-subtitle">
          Your workspace is active — upload a document to get started.
        </div>
      </div>

      {/* Metrics */}
      <div className="metrics-grid">
        {[
          { label: "Documents Used", value: user?.usage?.used ?? 0, sub: `${user?.usage?.remaining ?? 0} remaining` },
          { label: "Monthly Limit", value: user?.usage?.limit ?? 10, sub: `${user?.plan ?? "free"} plan` },
          { label: "Total Processed", value: documents.length, sub: "all time" },
          { label: "Plan", value: (user?.plan ?? "FREE").toUpperCase(), sub: "current plan", isText: true },
        ].map((m) => (
          <div key={m.label} className="metric-card">
            <div className="metric-label">{m.label}</div>
            <div className="metric-value serif">{m.value}</div>
            <div className="metric-change">{m.sub}</div>
          </div>
        ))}
      </div>

      {/* Usage bar */}
      {user?.usage && (
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
            {!user.usage.limit_reached && user.plan === "free" && (
              <button className="upgrade-pill">
                <div>
                  <div className="upgrade-label">Upgrade to Starter</div>
                  <div className="upgrade-sub">100 docs · $12/month</div>
                </div>
                <span className="upgrade-arrow">→</span>
              </button>
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
          {isLoading ? (
            <div style={{ padding: "40px", textAlign: "center", color: "#6B6860", fontSize: 13 }}>
              Loading...
            </div>
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
          {/* Upload CTA */}
          <Link href="/dashboard/upload" style={{ textDecoration: "none", display: "block" }}>
            <button className="upload-card">
              <div className="upload-card-icon">↑</div>
              <div className="upload-card-title serif">Upload a document</div>
              <div className="upload-card-sub">
                PDF, image, or scanned file.<br />Results in under 5 seconds.
              </div>
              <div className="upload-card-btn">Choose file →</div>
            </button>
          </Link>

          {/* Upgrade CTA */}
          {user?.plan === "free" && (
            <div className="card">
              <div style={{ padding: "20px" }}>
                <div className="serif" style={{ fontSize: 16, fontWeight: 600, color: "#1A1916", marginBottom: 6 }}>
                  Upgrade to Starter
                </div>
                <p style={{ fontSize: 12, color: "#6B6860", lineHeight: 1.6, marginBottom: 14 }}>
                  100 documents/month + Google Sheets export for $12/month.
                </p>
                <Link href="/dashboard/billing" className="btn-amber" style={{ width: "100%", justifyContent: "center" }}>
                  Upgrade plan →
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}