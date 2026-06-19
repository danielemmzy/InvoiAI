"use client";
// History page — /dashboard/history

import { useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Filter, Loader2 } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import DocumentRow from "@/components/documents/DocumentRow";
import { useDocuments, useIndustries } from "@/hooks/useDocuments";

export default function HistoryPage() {
  const [selectedIndustry, setSelectedIndustry] = useState<string | undefined>();
  const { data: industries } = useIndustries();
  const { documents, total, isLoading, isError, nextPage, prevPage, hasMore, hasPrev, offset, limit } = useDocuments(selectedIndustry);

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="dash-page-header">
        <div className="section-label">§01 Monitor / Documents</div>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
          <div>
            <div className="dash-title serif">Documents</div>
            <div className="dash-subtitle">{total} document{total !== 1 ? "s" : ""} processed</div>
          </div>
          <Link href="/dashboard/upload" className="btn-primary" style={{ padding: "10px 20px", fontSize: 13 }}>
            ↑ Upload new
          </Link>
        </div>
      </div>

      {/* Industry filter */}
      <div className="filter-row">
        <div className="filter-label">
          <Filter size={11} /> Filter:
        </div>
        <button
          className={`filter-chip${!selectedIndustry ? " active" : ""}`}
          onClick={() => setSelectedIndustry(undefined)}
        >
          All
        </button>
        {(industries || []).slice(0, 8).map((ind) => (
          <button
            key={ind.value}
            className={`filter-chip${selectedIndustry === ind.value ? " active-amber" : ""}`}
            onClick={() => setSelectedIndustry(selectedIndustry === ind.value ? undefined : ind.value)}
          >
            {ind.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="card">
        <div className="table-header">
          <span>Document</span>
          <span>Industry</span>
          <span>Status</span>
          <span>Export</span>
        </div>

        {isLoading ? (
          <div style={{ padding: "48px", textAlign: "center" }}>
            <Loader2 size={24} color="#C8922A" className="animate-spin" />
          </div>
        ) : isError ? (
          <div style={{ padding: "32px", textAlign: "center", fontSize: 13, color: "#E57373" }}>
            Failed to load documents. Please refresh.
          </div>
        ) : documents.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📂</div>
            <div className="empty-title serif">No documents yet</div>
            <div className="empty-desc">
              {selectedIndustry
                ? "No documents found for this filter."
                : "Upload your first invoice to get started."}
            </div>
            <Link href="/dashboard/upload" className="btn-primary">Upload document</Link>
          </div>
        ) : (
          documents.map((doc) => <DocumentRow key={doc.id} doc={doc} />)
        )}
      </div>

      {/* Pagination */}
      {(hasPrev || hasMore) && (
        <div className="pagination">
          <p className="pagination-info">
            Showing {offset + 1}–{Math.min(offset + limit, total)} of {total}
          </p>
          <div className="pagination-btns">
            <button className="page-btn" onClick={prevPage} disabled={!hasPrev}>
              <ChevronLeft size={13} /> Previous
            </button>
            <button className="page-btn" onClick={nextPage} disabled={!hasMore}>
              Next <ChevronRight size={13} />
            </button>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}