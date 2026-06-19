"use client";
// Document detail page — /dashboard/document/[id]

import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, AlertTriangle, Loader2 } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useDocument } from "@/hooks/useDocuments";
import { useExport } from "@/hooks/useExport";
import { getConfidenceBadge } from "@/lib/utils";

type SectionDict = Record<string, string | number | boolean | null | undefined>;

function isSectionDict(val: unknown): val is SectionDict {
  return typeof val === "object" && val !== null && !Array.isArray(val);
}

function renderVal(val: unknown): string {
  if (val == null) return "—";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

export default function DocumentPage() {
  const params = useParams();
  const id = params?.id as string;
  const { data, isLoading, isError } = useDocument(id);
  const { downloadExcel, isDownloadingExcel, downloadCsv, isDownloadingCsv, exportToSheets, isExportingToSheets } = useExport();

  if (isLoading) return (
    <DashboardLayout>
      <div className="spinner-page" style={{ minHeight: "60vh" }}>
        <Loader2 size={28} color="#C8922A" className="animate-spin" />
        <span className="spinner-label">Loading document...</span>
      </div>
    </DashboardLayout>
  );

  if (isError || !data) return (
    <DashboardLayout>
      <div className="empty-state">
        <div className="empty-icon">📭</div>
        <div className="empty-title serif">Document not found</div>
        <Link href="/dashboard/history" className="btn-primary">← Back to history</Link>
      </div>
    </DashboardLayout>
  );

  const conf = getConfidenceBadge(data.structured_data?.extraction_confidence);

  return (
    <DashboardLayout>
      {/* Back */}
      <Link href="/dashboard/history" className="back-link">
        <ArrowLeft size={14} /> Back to documents
      </Link>

      {/* Header */}
      <div className="doc-result-header">
        <div>
          <div className="section-label" style={{ marginBottom: 8 }}>§02 Document Result</div>
          <div className="doc-result-title serif">{data.document_type || "Document"}</div>
          <div className="doc-result-badges">
            <span className="badge badge-industry">
              {data.structured_data?.industry || "general"}
            </span>
            <span className="badge badge-done">✓ Done</span>
            <span className="badge" style={{ background: conf.bg, color: conf.color }}>
              {conf.label} confidence
            </span>
          </div>
        </div>
      </div>

      {/* Warnings */}
      {data.validation_warnings?.length > 0 && (
        <div className="warning-box">
          <AlertTriangle size={16} color="#C8922A" style={{ flexShrink: 0, marginTop: 2 }} />
          <div>
            <div className="warning-title">Validation warnings</div>
            {data.validation_warnings.map((w, i) => (
              <p key={i} className="warning-text">• {w}</p>
            ))}
          </div>
        </div>
      )}

      {/* Export */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="export-panel">
          <div className="export-panel-label">Export this document</div>
          <div className="export-buttons">
            <button
              className="export-btn"
              onClick={() => downloadExcel(id)}
              disabled={isDownloadingExcel}
            >
              {isDownloadingExcel ? <Loader2 size={14} className="animate-spin" /> : "⊞"}
              Download Excel
            </button>
            <button
              className="export-btn"
              onClick={() => downloadCsv(id)}
              disabled={isDownloadingCsv}
            >
              {isDownloadingCsv ? <Loader2 size={14} className="animate-spin" /> : "≡"}
              Download CSV
            </button>
            <button
              className="export-btn sheets"
              onClick={() => exportToSheets(id)}
              disabled={isExportingToSheets}
            >
              {isExportingToSheets ? <Loader2 size={14} className="animate-spin" /> : "↗"}
              Export to Sheets
            </button>
          </div>
        </div>
      </div>

      {/* Sections */}
      {data.structured_data?.sections &&
        Object.entries(data.structured_data.sections).map(([name, sectionData]) => (
          <div key={name} className="card section-card">
            <div className="section-card-header">
              <div className="section-card-name">{name.replace(/_/g, " ")}</div>
            </div>

            {Array.isArray(sectionData) && sectionData.length > 0 ? (
              <div style={{ overflowX: "auto" }}>
                <table className="section-table">
                  <thead>
                    <tr>
                      {isSectionDict(sectionData[0]) &&
                        Object.keys(sectionData[0]).map((k) => (
                          <th key={k}>{k.replace(/_/g, " ")}</th>
                        ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(sectionData as unknown[]).map((row, i) => (
                      <tr key={i}>
                        {isSectionDict(row) &&
                          Object.values(row).map((val, j) => (
                            <td key={j}>{renderVal(val)}</td>
                          ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div>
                {isSectionDict(sectionData) &&
                  Object.entries(sectionData).map(([key, val]) => (
                    <div key={key} className="kv-row">
                      <span className="kv-key">{key.replace(/_/g, " ")}</span>
                      <span className="kv-val">{renderVal(val)}</span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        ))}

      {/* Totals */}
      {data.structured_data?.raw_totals &&
        Object.keys(data.structured_data.raw_totals).length > 0 && (
          <div className="card section-card">
            <div className="section-card-header">
              <div className="section-card-name">Totals</div>
            </div>
            {Object.entries(data.structured_data.raw_totals).map(([key, val]) => (
              <div key={key} className="totals-row">
                <span className="totals-key">{key.replace(/_/g, " ")}</span>
                <span className="totals-val serif">
                  {typeof val === "number" ? val.toLocaleString() : String(val)}
                </span>
              </div>
            ))}
          </div>
        )}
    </DashboardLayout>
  );
}