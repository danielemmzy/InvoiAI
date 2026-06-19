"use client";
// DocumentRow — single row in history table

import Link from "next/link";
import { Trash2, Loader2 } from "lucide-react";
import { HistoryItem } from "@/types";
import { useDeleteDocument } from "@/hooks/useDocuments";
import { useExport } from "@/hooks/useExport";
import { formatRelativeTime, getFileIcon } from "@/lib/utils";

interface DocumentRowProps {
  doc: HistoryItem;
}

export default function DocumentRow({ doc }: DocumentRowProps) {
  const { mutate: deleteDoc, isPending: isDeleting } = useDeleteDocument();
  const { downloadExcel, isDownloadingExcel, downloadCsv, isDownloadingCsv, exportToSheets, isExportingToSheets } = useExport();

  return (
    <div className="doc-row">
      {/* Icon */}
      <div className="doc-icon">
        {getFileIcon(doc.file_type, doc.file_name)}
      </div>

      {/* Info */}
      <div className="doc-info">
        <Link href={`/dashboard/document/${doc.id}`} className="doc-name" style={{ textDecoration: "none" }}>
          {doc.file_name}
        </Link>
        <div className="doc-meta">
          {formatRelativeTime(doc.created_at)}
          {doc.document_type && ` · ${doc.document_type}`}
        </div>
      </div>

      {/* Badges */}
      <div className="doc-badges">
        <span className="badge badge-industry">{doc.industry}</span>
        {doc.status === "done" && <span className="badge badge-done">✓ Done</span>}
        {doc.status === "failed" && <span className="badge badge-error">Failed</span>}
        {doc.status === "processing" && <span className="badge badge-muted">Processing</span>}
        {doc.validation_warnings?.length > 0 && (
          <span className="badge badge-warning">
            {doc.validation_warnings.length} warning{doc.validation_warnings.length > 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Export buttons */}
      {doc.status === "done" && (
        <div className="doc-actions">
          <button
            className="doc-action-btn"
            title="Download Excel"
            onClick={(e) => { e.stopPropagation(); downloadExcel(doc.id); }}
            disabled={isDownloadingExcel}
          >
            {isDownloadingExcel ? <Loader2 size={11} className="animate-spin" /> : "⊞"}
          </button>
          <button
            className="doc-action-btn"
            title="Download CSV"
            onClick={(e) => { e.stopPropagation(); downloadCsv(doc.id); }}
            disabled={isDownloadingCsv}
          >
            {isDownloadingCsv ? <Loader2 size={11} className="animate-spin" /> : "≡"}
          </button>
          <button
            className={`doc-action-btn${doc.sheets_url ? " sheets" : ""}`}
            title={doc.sheets_url ? "Open Google Sheets" : "Export to Sheets"}
            onClick={(e) => {
              e.stopPropagation();
              if (doc.sheets_url) window.open(doc.sheets_url, "_blank");
              else exportToSheets(doc.id);
            }}
            disabled={isExportingToSheets}
          >
            {isExportingToSheets ? <Loader2 size={11} className="animate-spin" /> : "↗"}
          </button>
        </div>
      )}

      {/* Delete */}
      <button
        className="doc-action-btn"
        title="Delete"
        onClick={(e) => {
          e.stopPropagation();
          if (confirm("Delete this document?")) deleteDoc(doc.id);
        }}
        disabled={isDeleting}
        style={{ color: "#AAA8A0" }}
      >
        {isDeleting ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
      </button>
    </div>
  );
}