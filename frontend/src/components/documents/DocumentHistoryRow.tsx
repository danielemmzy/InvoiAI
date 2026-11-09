"use client";

import Link from "next/link";
import { ChevronRight, Loader2, Pencil, Eye, AlertTriangle, RotateCcw } from "lucide-react";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { documentsApi } from "@/api/documents";
import { getErrorMessage } from "@/api/client";
import { useAppStore } from "@/store/useAppStore";
import { HistoryItem } from "@/types";
import { getFileIcon, formatRelativeTime } from "@/lib/utils";

function money(value: unknown, currency?: string | null): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: currency || "USD", maximumFractionDigits: 2 }).format(n);
  } catch { return `${currency || ""} ${n.toLocaleString()}`.trim(); }
}

function typeLabel(value?: string): string {
  return String(value || "unknown").replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function isCapturing(doc: HistoryItem): boolean {
  return ["pending", "processing"].includes(String(doc.capture_status || ""));
}

export default function DocumentHistoryRow({ doc }: { doc: HistoryItem }) {
  const queryClient = useQueryClient();
  const workspaceId = useAppStore((state) => state.activeWorkspace?.id);
  const [retrying, setRetrying] = useState(false);
  const loading = isCapturing(doc);
  const progress = Math.max(0, Math.min(100, Number(doc.capture_progress || 0)));
  const failed = doc.capture_status === "failed" || doc.intelligence_status === "failed" || doc.processing_step === "failed" || doc.status === "failed";
  const ready = doc.capture_status === "complete";
  const type = loading ? "Reading…" : typeLabel(doc.document_type);
  const vendor = loading ? "—" : (doc.vendor_name || "—");
  const invoiceNumber = loading ? "—" : (doc.document_number || "—");
  const qty = loading ? "—" : (doc.total_quantity == null ? "—" : Number(doc.total_quantity).toLocaleString());
  const total = loading ? "—" : money(doc.total_amount, doc.currency);
  const account = loading ? "—" : (doc.account_name || doc.account_code || "—");

  const retry = async () => {
    if (retrying) return;
    setRetrying(true);
    try {
      await documentsApi.retryProcessing(doc.id);
      await queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] });
      await queryClient.invalidateQueries({ queryKey: ["document", workspaceId, doc.id] });
      await queryClient.invalidateQueries({ queryKey: ["document-intelligence", workspaceId, doc.id] });
      toast.success(`Retry queued for ${doc.file_name}.`);
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not retry this upload."));
    } finally { setRetrying(false); }
  };

  return (
    <div className="document-history-table-row">
      <div className="history-document-cell">
        <div className="history-file-icon">{getFileIcon(doc.file_type, doc.file_name)}</div>
        <div className="history-file-copy">
          <div className="history-file-name" title={doc.file_name}>{doc.file_name}</div>
          <div className="history-file-meta">{formatRelativeTime(doc.created_at)} · {doc.line_item_count ?? 0} line item{doc.line_item_count === 1 ? "" : "s"}</div>
        </div>
      </div>

      <div className="history-data-cell"><span className="history-mobile-label">Type</span>{loading ? <span className="history-loading-text"><Loader2 size={12} className="animate-spin"/> {type}</span> : <span className="history-type-pill">{type}</span>}</div>
      <div className="history-data-cell"><span className="history-mobile-label">Vendor</span>{vendor}</div>
      <div className="history-data-cell"><span className="history-mobile-label">Invoice / PO #</span>{invoiceNumber}</div>
      <div className="history-data-cell numeric"><span className="history-mobile-label">Price</span>{loading ? "—" : money(doc.subtotal ?? doc.total_amount, doc.currency)}</div>
      <div className="history-data-cell numeric"><span className="history-mobile-label">Qty</span>{qty}</div>
      <div className="history-data-cell numeric strong"><span className="history-mobile-label">Total</span>{total}</div>
      <div className="history-data-cell"><span className="history-mobile-label">Account</span>{account}</div>

      <div className="history-status-cell">
        {loading ? (
          <div className="history-progress-wrap">
            <div className="history-progress-top"><span>Loading data</span><strong>{progress}%</strong></div>
            <div className="history-progress"><div style={{ width: `${progress}%` }}/></div>
          </div>
        ) : failed ? (
          <span className="history-status danger"><AlertTriangle size={12}/> Failed</span>
        ) : ready ? (
          <span className="history-status good">Ready</span>
        ) : (
          <span className="history-status">Queued</span>
        )}
      </div>

      <div className="history-actions-cell">
        <Link href={`/dashboard/document/${doc.id}`} className="history-action-btn" title="Preview document"><Eye size={14}/> <span>Preview</span></Link>
        <Link href={`/dashboard/document/${doc.id}?edit=1`} className="history-action-btn secondary" title="Edit captured data"><Pencil size={14}/> <span>Edit</span></Link>
        {failed && <button type="button" className="history-action-btn secondary" title="Retry this failed upload" onClick={() => void retry()} disabled={retrying} style={{ opacity: retrying ? 0.65 : 1, cursor: retrying ? "wait" : "pointer" }}>{retrying ? <Loader2 size={14} className="animate-spin"/> : <RotateCcw size={14}/>}<span>{retrying ? "Retrying…" : "Retry"}</span></button>}
        <Link href={`/dashboard/document/${doc.id}`} className="history-icon-btn" title="Open document"><ChevronRight size={15}/></Link>
      </div>
    </div>
  );
}
