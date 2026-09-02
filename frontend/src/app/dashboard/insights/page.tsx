"use client";
// Insights — /dashboard/insights

import { AlertTriangle, TrendingUp, Wallet, Copy, Clock3, Sparkles, RefreshCw, X, Loader2, Bell } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError, EmptyState } from "@/components/ui/PageState";
import { useInsights, useGenerateInsights, useDismissInsight } from "@/hooks/useApprovalsInsightsPO";
import type { InsightRow, InsightType } from "@/api/insights";

const TYPE_ICON: Record<InsightType, typeof AlertTriangle> = {
  overdue: Clock3,
  price_increase: TrendingUp,
  anomaly: Sparkles,
  cashflow: Wallet,
  duplicate: Copy,
};

const TYPE_LABEL: Record<InsightType, string> = {
  overdue: "Overdue",
  price_increase: "Price increase",
  anomaly: "Anomaly",
  cashflow: "Cash flow",
  duplicate: "Duplicate",
};

export default function InsightsPage() {
  const insights = useInsights();
  const generate = useGenerateInsights();
  const dismiss = useDismissInsight();

  const active = (insights.data ?? []).filter((i) => !i.is_dismissed);
  const critical = active.filter((i) => i.severity === "critical").length;
  const warning = active.filter((i) => i.severity === "warning").length;

  return (
    <DashboardLayout>
      <div className="page-head">
        <div>
          <div className="eyebrow">Proactive insights</div>
          <h1 className="page-title">Insights</h1>
          <p className="page-subtitle">
            What the analyzer found without being asked, ranked by how much it matters.
          </p>
        </div>
        <button type="button" className="btn-secondary" onClick={() => generate.mutate()} disabled={generate.isPending}>
          {generate.isPending ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />} Run scan now
        </button>
      </div>

      {!insights.isLoading && !insights.isError && (
        <div className="ap-metric-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
          <div className="ap-metric-card danger">
            <div className="ap-metric-icon"><AlertTriangle /></div>
            <div><div className="ap-metric-label">Critical</div><div className="ap-metric-value">{critical}</div></div>
          </div>
          <div className="ap-metric-card warn">
            <div className="ap-metric-icon"><Bell /></div>
            <div><div className="ap-metric-label">Warning</div><div className="ap-metric-value">{warning}</div></div>
          </div>
          <div className="ap-metric-card">
            <div className="ap-metric-icon"><Sparkles /></div>
            <div><div className="ap-metric-label">Total active</div><div className="ap-metric-value">{active.length}</div></div>
          </div>
        </div>
      )}

      {insights.isLoading ? (
        <PageLoading variant="table" rows={5} />
      ) : insights.isError ? (
        <PageError title="Couldn't load insights" onRetry={insights.refetch} />
      ) : !active.length ? (
        <EmptyState
          icon={Sparkles}
          title="Nothing flagged right now"
          message="The analyzer runs daily against your synced data. Run it manually if you want a check right now."
          action={<button className="btn-secondary" onClick={() => generate.mutate()}><RefreshCw size={13} /> Run scan now</button>}
        />
      ) : (
        <div className="insight-feed">
          {active.map((insight) => (
            <InsightRowItem key={insight.id} insight={insight} onDismiss={() => dismiss.mutate(insight.id)} />
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}

function InsightRowItem({ insight, onDismiss }: { insight: InsightRow; onDismiss: () => void }) {
  const Icon = TYPE_ICON[insight.insight_type] || Sparkles;
  const tone = insight.severity === "critical" ? "danger" : insight.severity === "warning" ? "warn" : "neutral";

  return (
    <div className={`insight-feed-row ${tone}`}>
      <div className={`insight-feed-icon ${tone}`}><Icon size={16} /></div>
      <div className="insight-feed-body">
        <div className="insight-feed-top">
          <span className={`status-pill ${tone}`}>{TYPE_LABEL[insight.insight_type]}</span>
          {!insight.is_read && <span className="insight-feed-new">New</span>}
        </div>
        <div className="insight-feed-title">{insight.title}</div>
        <div className="insight-feed-desc">{insight.description}</div>
        {insight.recommended_action && (
          <div className="insight-feed-action">Suggested: {insight.recommended_action}</div>
        )}
      </div>
      <button type="button" className="insight-feed-dismiss" onClick={onDismiss} aria-label="Dismiss insight">
        <X size={14} />
      </button>
    </div>
  );
}
