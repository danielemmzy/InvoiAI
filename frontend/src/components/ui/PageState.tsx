"use client";
// Shared data-fetching states for dashboard pages.
//
// The pattern every page should follow:
//   if (query.isLoading)               → <PageLoading variant="..." />
//   if (query.isError)                 → <PageError onRetry={query.refetch} />
//   if (!data || data.length === 0)    → <EmptyState ... />
//   otherwise                          → render the real content
//
// PageLoading renders a skeleton shaped like the content that's coming,
// not a spinner parked in the middle of the page — a spinner tells the
// user nothing about what's about to appear or how long it usually takes.

import { AlertTriangle, RefreshCw, Inbox, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/* ── Loading ───────────────────────────────────────────────── */

type LoadingVariant = "cards" | "table" | "chart" | "page";

export function PageLoading({
  variant = "page",
  rows = 5,
  cards = 4,
}: {
  variant?: LoadingVariant;
  rows?: number;
  cards?: number;
}) {
  if (variant === "cards") {
    return (
      <div className="skeleton-grid" aria-busy="true" aria-label="Loading">
        {Array.from({ length: cards }).map((_, i) => (
          <div key={i} className="skeleton-card">
            <div className="skeleton-line" style={{ width: "40%", height: 11 }} />
            <div className="skeleton-line" style={{ width: "65%", height: 26, marginTop: 10 }} />
            <div className="skeleton-line" style={{ width: "50%", height: 10, marginTop: 10 }} />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className="skeleton-table" aria-busy="true" aria-label="Loading">
        <div className="skeleton-table-head">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton-line" style={{ width: "70%", height: 10 }} />
          ))}
        </div>
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="skeleton-table-row">
            {Array.from({ length: 5 }).map((_, c) => (
              <div key={c} className="skeleton-line" style={{ width: c === 0 ? "80%" : "55%", height: 11 }} />
            ))}
          </div>
        ))}
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <div className="skeleton-chart" aria-busy="true" aria-label="Loading">
        <div className="skeleton-line" style={{ width: "30%", height: 12, marginBottom: 18 }} />
        <div className="skeleton-chart-bars">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="skeleton-bar" style={{ height: `${28 + ((i * 37) % 60)}%` }} />
          ))}
        </div>
      </div>
    );
  }

  // full page: header + a card grid + a table, a reasonable default shape
  return (
    <div aria-busy="true" aria-label="Loading page">
      <div className="skeleton-line" style={{ width: 220, height: 13, marginBottom: 10 }} />
      <div className="skeleton-line" style={{ width: 340, height: 24, marginBottom: 28 }} />
      <PageLoading variant="cards" cards={cards} />
      <div style={{ height: 20 }} />
      <PageLoading variant="table" rows={rows} />
    </div>
  );
}

/* ── Error ─────────────────────────────────────────────────── */

export function PageError({
  title = "This section couldn't load",
  message = "Something went wrong while fetching this data.",
  onRetry,
  compact = false,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
  compact?: boolean;
}) {
  return (
    <div className={`page-error${compact ? " compact" : ""}`} role="alert">
      <div className="page-error-icon">
        <AlertTriangle size={compact ? 16 : 20} />
      </div>
      <div className="page-error-body">
        <div className="page-error-title">{title}</div>
        <div className="page-error-message">{message}</div>
      </div>
      {onRetry && (
        <button type="button" className="page-error-retry" onClick={onRetry}>
          <RefreshCw size={13} /> Retry
        </button>
      )}
    </div>
  );
}

/* ── Empty ─────────────────────────────────────────────────── */

export function EmptyState({
  icon: Icon = Inbox,
  title,
  message,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  message?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state-block">
      <div className="empty-state-icon">
        <Icon size={20} />
      </div>
      <div className="empty-state-title">{title}</div>
      {message && <div className="empty-state-message">{message}</div>}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
}
