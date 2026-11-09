"use client";
// History page — /dashboard/history

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Activity, AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, Filter, Loader2, Search, Upload, X } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import DocumentHistoryRow from "@/components/documents/DocumentHistoryRow";
import { useDocuments, useIndustries } from "@/hooks/useDocuments";

function HistoryContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const selectedIndustry = searchParams.get("industry") || undefined;
  const [searchInput, setSearchInput] = useState(searchParams.get("query") || "");
  const query = searchParams.get("query") || undefined;
  const { data: industries } = useIndustries();
  const { documents, total, isLoading, isError, nextPage, prevPage, hasMore, hasPrev, offset, limit } = useDocuments(selectedIndustry, query);

  const updateFilters = (nextIndustry?: string, nextQuery?: string) => {
    const params = new URLSearchParams(searchParams.toString());
    nextIndustry ? params.set("industry", nextIndustry) : params.delete("industry");
    nextQuery?.trim() ? params.set("query", nextQuery.trim()) : params.delete("query");
    router.replace(params.size ? `${pathname}?${params}` : pathname);
  };

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    updateFilters(selectedIndustry, searchInput);
  };

  const acceptedOnPage = documents.filter((d) => d.status === "approved").length;
  const reviewOnPage = documents.filter((d) => d.status === "needs_review").length;
  const processingOnPage = documents.filter((d) => ["pending", "processing"].includes(String(d.capture_status)) || ["queued", "processing"].includes(String(d.intelligence_status))).length;
  const failedOnPage = documents.filter((d) => d.status === "failed" || d.processing_step === "failed").length;

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
            <Upload size={14} style={{ verticalAlign: "-2px", marginRight: 6 }} /> Upload new
          </Link>
        </div>
      </div>

      {/* Workflow overview */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginBottom: 18 }}>
        <div className="card" style={{ padding: 15 }}><div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>Total documents</div><div style={{ fontSize: 25, fontWeight: 700, marginTop: 4 }}>{total}</div><div className="muted" style={{ fontSize: 12, marginTop: 3 }}>Workspace history</div></div>
        <div className="card" style={{ padding: 15 }}><div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>Accepted</div><div style={{ fontSize: 25, fontWeight: 700, marginTop: 4 }}>{acceptedOnPage}</div><div className="muted" style={{ fontSize: 12, marginTop: 3 }}><CheckCircle2 size={12} style={{ verticalAlign: "-2px" }} /> On this page</div></div>
        <div className="card" style={{ padding: 15 }}><div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>Needs attention</div><div style={{ fontSize: 25, fontWeight: 700, marginTop: 4 }}>{reviewOnPage + failedOnPage}</div><div className="muted" style={{ fontSize: 12, marginTop: 3 }}><AlertTriangle size={12} style={{ verticalAlign: "-2px" }} /> Review / failed</div></div>
        <div className="card" style={{ padding: 15 }}><div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>Processing</div><div style={{ fontSize: 25, fontWeight: 700, marginTop: 4 }}>{processingOnPage}</div><div className="muted" style={{ fontSize: 12, marginTop: 3 }}><Activity size={12} style={{ verticalAlign: "-2px" }} /> Active pipeline</div></div>
      </div>

      {/* Industry filter */}
      <div className="filter-row">
        <div className="filter-label">
          <Filter size={11} /> Filter:
        </div>
        <button
          className={`filter-chip${!selectedIndustry ? " active" : ""}`}
          aria-pressed={!selectedIndustry}
          onClick={() => updateFilters(undefined, query)}
        >
          All
        </button>
        {(industries || []).slice(0, 8).map((ind) => (
          <button
            key={ind.value}
            className={`filter-chip${selectedIndustry === ind.value ? " active-amber" : ""}`}
            aria-pressed={selectedIndustry === ind.value}
            onClick={() => updateFilters(selectedIndustry === ind.value ? undefined : ind.value, query)}
          >
            {ind.label}
          </button>
        ))}
      </div>

      {/* History table */}
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ padding: "14px 16px", borderBottom: "1px solid #E9E4DA", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <div>
            <div className="section-card-name">Document history</div>
            <div className="muted" style={{ fontSize: 11, marginTop: 3 }}>Every upload gets a row immediately. Captured fields populate live as extraction finishes.</div>
          </div>
          <span className="badge">Live capture</span>
        </div>
        <form onSubmit={submitSearch} style={{ display: "flex", gap: 8, padding: "12px 16px", borderBottom: "1px solid #E9E4DA" }}>
          <label htmlFor="document-search" className="sr-only">Search invoice number or vendor</label>
          <div style={{ position: "relative", flex: 1 }}>
            <Search aria-hidden="true" size={15} style={{ position: "absolute", left: 10, top: 10, color: "#827B70" }} />
            <input id="document-search" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Search invoice number or vendor" style={{ width: "100%", minHeight: 36, padding: "8px 34px", border: "1px solid #E9E4DA", borderRadius: 8 }} />
            {searchInput && <button type="button" aria-label="Clear search" onClick={() => { setSearchInput(""); updateFilters(selectedIndustry); }} style={{ position: "absolute", right: 4, top: 3, minWidth: 30, minHeight: 30, color: "#827B70" }}><X aria-hidden="true" size={15} /></button>}
          </div>
          <button className="page-btn" type="submit">Search</button>
        </form>

        {isLoading ? (
          <div style={{ padding: "48px", textAlign: "center" }}>
            <Loader2 size={24} color="#C8922A" className="animate-spin" />
          </div>
        ) : isError ? (
          <div style={{ padding: "32px", textAlign: "center", fontSize: 13, color: "#E57373" }}>Failed to load documents. Please refresh.</div>
        ) : documents.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📂</div>
            <div className="empty-title serif">No documents yet</div>
            <div className="empty-desc">{selectedIndustry || query ? "No documents match these filters. Clear them or check the invoice number." : "Upload your first invoice, receipt, or purchase order to get started."}</div>
            {(selectedIndustry || query) && <button className="page-btn" onClick={() => { setSearchInput(""); updateFilters(); }}>Clear filters</button>}
            <Link href="/dashboard/upload" className="btn-primary">Upload document</Link>
          </div>
        ) : (
          <div className="document-history-table">
            <div className="document-history-table-row" style={{ background: "#F8F5EE", borderTop: 0, fontSize: 9, textTransform: "uppercase", letterSpacing: ".06em", color: "#827B70", fontWeight: 700 }}>
              <span>Document</span><span>Type</span><span>Vendor</span><span>Invoice / PO #</span><span style={{ textAlign: "right" }}>Price</span><span style={{ textAlign: "right" }}>Qty</span><span style={{ textAlign: "right" }}>Total</span><span>Account</span><span style={{ textAlign: "right" }}>Status / Actions</span>
            </div>
            {documents.map((doc) => <DocumentHistoryRow key={doc.id} doc={doc} />)}
          </div>
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

export default function HistoryPage() {
  return <Suspense fallback={null}><HistoryContent /></Suspense>;
}
