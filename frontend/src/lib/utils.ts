// ─────────────────────────────────────────────
// Utils — shared helper functions
// ─────────────────────────────────────────────

import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(dateString?: string): string {
  if (!dateString) return "—";
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatRelativeTime(dateString?: string): string {
  if (!dateString) return "—";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "Yesterday";
  return `${diffDays} days ago`;
}

export function getConfidenceBadge(confidence?: string): {
  label: string;
  color: string;
  bg: string;
} {
  switch (confidence) {
    case "high":
      return { label: "High", color: "#1E7E4B", bg: "#EAFAF1" };
    case "medium":
      return { label: "Medium", color: "#8B6420", bg: "#FFF8E1" };
    case "low":
      return { label: "Low", color: "#C0392B", bg: "#FDECEA" };
    default:
      return { label: "Unknown", color: "#666", bg: "#F5F5F5" };
  }
}

export function getFileIcon(fileType: string, fileName: string): string {
  if (fileType === "pdf" || fileName.endsWith(".pdf")) return "📄";
  if (fileType === "image") return "🖼️";
  return "📎";
}

export function formatCurrency(amount?: number, currency = "USD"): string {
  if (amount == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(amount);
}

export function truncate(str: string, length: number): string {
  return str.length > length ? str.slice(0, length) + "..." : str;
}