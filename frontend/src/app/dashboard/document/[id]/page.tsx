"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  Database,
  Download,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Loader2,
  Play,
  ShieldAlert,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import DocumentProcessingTimeline from "@/components/documents/DocumentProcessingTimeline";
import { useDocument, useDocumentIntelligence } from "@/hooks/useDocuments";
import { useExport } from "@/hooks/useExport";
import { apApi } from "@/api/ap";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { getConfidenceBadge } from "@/lib/utils";
import { documentsApi } from "@/api/documents";
import { getErrorMessage } from "@/api/client";
import APMatchingPanel from "@/components/documents/APMatchingPanel";
import PaymentLifecyclePanel from "@/components/ap/PaymentLifecyclePanel";
import DocumentCaptureEditor from "@/components/documents/DocumentCaptureEditor";

type Issue = { title: string; text: string; high: boolean };
type ModuleResult = {
  summary?: string;
  reasons?: unknown[];
  warnings?: unknown[];
  metadata?: Record<string, unknown>;
};

type LineItem = {
  description?: unknown;
  quantity?: unknown;
  unit_price?: unknown;
  amount?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asModuleResult(value: unknown): ModuleResult | null {
  return isRecord(value) ? (value as ModuleResult) : null;
}

function moduleAvailable(value: unknown): boolean {
  return asModuleResult(value)?.metadata?.available !== false;
}

function text(value: unknown, fallback = "—"): string {
  if (value == null || value === "") return fallback;
  return String(value);
}

function labelize(value: string): string {
  return value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function humanValue(value: unknown, fallback = "—"): string {
  if (value == null || value === "") return fallback;
  if (Array.isArray(value)) return value.map((item) => humanValue(item)).join(", ");
  if (isRecord(value)) {
    return Object.entries(value)
      .map(([key, item]) => `${labelize(key)}: ${humanValue(item)}`)
      .join(" · ");
  }
  return String(value);
}

function capturedValue(key: string, value: unknown): string {
  if (key.toLowerCase().includes("tax_rate") || key.toLowerCase().includes("tax rate")) {
    const n = Number(value);
    if (Number.isFinite(n)) return `${n <= 1 ? n * 100 : n}%`;
  }
  return humanValue(value);
}

function scoreLabel(score?: number): string {
  if (score == null) return "—";
  if (score >= 85) return "Strong";
  if (score >= 70) return "Review";
  if (score >= 50) return "Concern";
  return "High risk";
}

function formatDate(value: unknown): string {
  if (!value) return "—";
  const raw = String(value);
  const date = new Date(`${raw}T00:00:00`);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatMoney(value: unknown, currency?: unknown): string {
  if (value == null || value === "") return "—";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);
  const code = typeof currency === "string" && currency.trim() ? currency : undefined;
  try {
    return new Intl.NumberFormat(undefined, {
      style: code ? "currency" : "decimal",
      currency: code,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return amount.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
}

function friendlyIssueText(issue: string, documentData: Record<string, unknown>): string {
  const lower = issue.toLowerCase();
  const vendorName = text(documentData.vendor_name, "the extracted vendor");
  const date = formatDate(documentData.document_date);

  if (lower.includes("document date is in the future")) {
    return `The document date is ${date}, which is in the future relative to today. Please confirm the date shown on the original document.`;
  }
  if (lower.includes("currency missing") || lower.includes("currency is required")) {
    return "No currency was captured from the document. Please confirm the currency shown on the original document.";
  }
  if (lower.includes("vendor record could not be resolved")) {
    return `InvoiAI extracted the vendor as “${vendorName}”, but could not match it to a known vendor record. Vendor intelligence cannot continue until a vendor record is resolved.`;
  }
  if (lower.includes("vendor checks could not be completed")) {
    return "The vendor was extracted from the document, but vendor intelligence could not be completed because the vendor record was not resolved.";
  }
  if (lower.includes("fraud analysis is unavailable")) {
    return "Fraud analysis is unavailable because the vendor could not be resolved to a known vendor record.";
  }
  if (lower.includes("fraud checks could not be fully completed")) {
    return "Fraud checks could not be fully completed with the vendor information currently available.";
  }
  if (lower.includes("no linked purchase order") || lower.includes("document has no linked purchase order")) {
    return "No purchase order is linked to this document. This is shown for review rather than as an OCR extraction failure.";
  }
  if (lower.includes("document file hash matches previous document")) {
    return "The uploaded file has the same file hash as a previous document, so InvoiAI is asking you to review it as a possible duplicate.";
  }
  if (lower.includes("duplicate similarity")) {
    return "InvoiAI found a high similarity with another document and is asking for a duplicate review.";
  }
  return issue;
}

function collectIssues(
  warnings: string[],
  analysis: any,
  vendor: any,
  documentData: Record<string, unknown>,
): Issue[] {
  const issues: Issue[] = [];
  const add = (title: string, value: unknown, high: boolean) => {
    if (value == null || String(value).trim() === "") return;
    const original = String(value);
    issues.push({ title, text: friendlyIssueText(original, documentData), high });
  };

  for (const warning of warnings) add("Validation", warning, true);

  const validation = asModuleResult(analysis?.module_results?.validation);
  for (const error of Array.isArray((validation as any)?.errors) ? (validation as any).errors : []) {
    add("Validation error", error, true);
  }
  for (const warning of Array.isArray(validation?.warnings) ? validation.warnings : []) {
    add("Validation warning", warning, true);
  }

  const modules: Array<[string, string]> = [
    ["OCR check", "ocr"],
    ["Math check", "math"],
    ["Vendor check", "vendor"],
    ["Duplicate check", "duplicate"],
    ["Historical check", "historical"],
    ["Purchase order check", "purchase_order"],
    ["Fraud / risk check", "fraud"],
    ["Compliance check", "compliance"],
  ];

  for (const [label, key] of modules) {
    const result = asModuleResult(analysis?.module_results?.[key]);
    if (!result) continue;

    if (result.metadata?.available === false) {
      add(`${label} unavailable`, result.summary || "This check could not be completed with the information currently available.", false);
    }
    for (const reason of Array.isArray(result.reasons) ? result.reasons : []) add(label, reason, true);
    for (const warning of Array.isArray(result.warnings) ? result.warnings : []) add(label, warning, false);
  }

  for (const signal of Array.isArray(analysis?.fraud_signals) ? analysis.fraud_signals : []) {
    add("Fraud / risk signal", signal, true);
  }

  if (analysis?.amount_anomaly) {
    add(
      "Amount anomaly",
      `The amount is unusual compared with the historical average (${analysis.amount_vs_avg_pct ?? "unknown"}% variance).`,
      true,
    );
  }
  if (vendor?.is_blocked) add("Vendor blocked", "This vendor is currently marked as blocked.", true);
  if (analysis?.is_duplicate) {
    add(
      "Possible duplicate",
      `This document has a duplicate similarity of ${analysis.duplicate_similarity ?? "high"}.`,
      true,
    );
  }

  return issues.filter((issue, index, all) =>
    all.findIndex((candidate) => candidate.title === issue.title && candidate.text === issue.text) === index,
  );
}

export default function DocumentPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = params?.id as string;
  const { data, isLoading, isError } = useDocument(id);
  const intelligence = useDocumentIntelligence(id);
  const { downloadExcel, isDownloadingExcel, downloadCsv, isDownloadingCsv, exportToSheets, isExportingToSheets } = useExport();
  const [runningAP, setRunningAP] = useState(false);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [reviewState, setReviewState] = useState<string | null>(null);
  const [apStatus, setApStatus] = useState<any | null>(null);
  const [apStarted, setApStarted] = useState(false);
  const [showAPMatching, setShowAPMatching] = useState(false);
  const [editingCapture, setEditingCapture] = useState(false);

  useEffect(() => {
    if (searchParams.get("ap") === "1") setShowAPMatching(true);
    if (searchParams.get("edit") === "1") setEditingCapture(true);
  }, [searchParams]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    const load = async () => {
      try {
        const status = await apApi.getStatus(id);
        if (!cancelled && status) {
          setApStatus(status);
          if (status.ap_status && status.ap_status !== "not_started") setApStarted(true);
        }
      } catch {
        // A document that has never entered AP may legitimately return no status.
      }
    };
    let timer: number | undefined;
    const poll = async () => {
      await load();
      if (!cancelled) timer = window.setTimeout(poll, apStarted ? 5000 : 9000);
    };
    void poll();
    return () => { cancelled = true; if (timer) window.clearTimeout(timer); };
  }, [id, apStarted]);

  if (isLoading) {
    return <DashboardLayout><div className="spinner-page" style={{ minHeight: "60vh" }}><Loader2 size={28} color="#C8922A" className="animate-spin"/><span className="spinner-label">Loading document...</span></div></DashboardLayout>;
  }
  if (isError || !data) {
    return <DashboardLayout><div className="empty-state"><div className="empty-icon">📭</div><div className="empty-title serif">Document not found</div><Link href="/dashboard/history" className="btn-primary">← Back to history</Link></div></DashboardLayout>;
  }

  // Normalize the API union once. UploadResponse intentionally contains only
  // the upload/history fields, while the intelligence endpoint returns the
  // richer document record (mime type, AP state, dates, totals, etc.).
  // Keeping the normalization here prevents the page from producing dozens
  // of union-property TypeScript errors.
  const documentRecord = data as unknown as Record<string, any>;
  const workflow = (intelligence.data ?? {}) as Record<string, any>;
  const processing = (workflow.document ?? documentRecord) as Record<string, any>;
  const analysis = workflow.analysis as any;
  const structured = (workflow.structured_data ?? documentRecord.structured_data ?? {}) as Record<string, any>;
  const documentData = (structured.sections?.document ?? {}) as Record<string, unknown>;
  const conf = getConfidenceBadge(structured?.extraction_confidence);
  const score = analysis?.overall_score ?? analysis?.health_score;
  const fraud = analysis?.fraud_score;
  const duplicate = analysis?.duplicate_score;
  const financial = analysis?.financial_score;
  const vendor = workflow?.vendor;
  const warnings = (processing?.validation_warnings || documentRecord.validation_warnings || []) as string[];
  const humanReviewStatus = String(processing?.human_review_status || documentRecord.human_review_status || "pending");
  const intelligenceStatus = String(processing?.intelligence_status || documentRecord.intelligence_status || "not_requested");
  const captureStatus = String(processing?.capture_status || documentRecord.capture_status || "pending");
  const captureProgress = Number(processing?.capture_progress ?? documentRecord.capture_progress ?? 0);
  const isFailed = intelligenceStatus === "failed" || captureStatus === "failed" || processing?.processing_step === "failed" || processing?.status === "failed";
  const isProcessing = intelligenceStatus === "queued" || intelligenceStatus === "processing";
  const isCapturing = captureStatus === "pending" || captureStatus === "processing";
  const captureReady = captureStatus === "complete";
  const isAccepted = captureReady;
  const analysisReady = intelligenceStatus === "complete" && !!analysis;
  const workflowUnlocked = captureReady;
  const moduleResults = analysis?.module_results || {};
  const fraudAvailable = moduleAvailable(moduleResults.fraud);
  const duplicateAvailable = moduleAvailable(moduleResults.duplicate);
  const rawOcrText = workflow?.ocr?.raw_text || (Array.isArray(workflow?.ocr?.pages) ? workflow.ocr.pages.map((page: any) => page?.text).filter(Boolean).join("\n\n") : "");
  const lineItems = Array.isArray(workflow?.line_items) ? workflow.line_items as LineItem[] : [];
  const currency = documentData.currency ?? processing?.currency ?? documentRecord.currency;
  const issues = collectIssues(warnings, analysis, vendor, documentData);
  const source = workflow?.source_document;
  const sourceUrl = source?.url as string | undefined;
  const sourceMimeType = String(source?.mime_type || processing?.mime_type || documentRecord.mime_type || "").toLowerCase();
  const isPdf = sourceMimeType === "application/pdf" || String(source?.file_type || processing?.file_type || documentRecord.file_type || "").toLowerCase() === "pdf";
  const isImage = sourceMimeType.startsWith("image/") || ["png", "jpg", "jpeg", "webp", "gif"].includes(String(source?.file_type || "").toLowerCase());

  const review = async (decision: "approve" | "reject") => {
    setReviewing(true);
    try {
      await documentsApi.review(id, decision);
      if (decision === "reject") {
        toast.success("Document declined and removed.");
        router.replace("/dashboard/history");
        router.refresh();
        return;
      }
      setReviewState("approved");
      await intelligence.refetch();
      toast.success("Document accepted. You can now run AI Analysis or AP Automation.");
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "Review could not be saved."));
    } finally { setReviewing(false); }
  };

  const markLiveProcessing = () => {
    if (typeof window === "undefined") return;
    const key = "invoiai-active-document-ids";
    try {
      const existing = JSON.parse(localStorage.getItem(key) || "[]");
      localStorage.setItem(key, JSON.stringify(Array.from(new Set([...existing, id])).slice(-20)));
    } catch {
      localStorage.setItem(key, JSON.stringify([id]));
    }
  };

  const runAIAnalysis = async () => {
    setRunningAnalysis(true);
    try {
      markLiveProcessing();
      await documentsApi.analyze(id);
      toast.success("Document Intelligence started.");
      await intelligence.refetch();
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "Could not start AI analysis."));
    } finally { setRunningAnalysis(false); }
  };

  const runAP = () => {
    setShowAPMatching(true);
  };

  const lineItemSum = lineItems.reduce((sum, item) => {
    const amount = Number(item.amount);
    return Number.isFinite(amount) ? sum + amount : sum;
  }, 0);
  const subtotal = processing?.subtotal ?? documentData.subtotal ?? structured?.raw_totals?.subtotal;
  const taxAmount = processing?.tax_amount ?? documentData.tax_amount ?? structured?.raw_totals?.tax_amount;
  const totalAmount = processing?.total_amount ?? documentData.total_amount ?? structured?.raw_totals?.total_amount;
  const amountDue = processing?.amount_due ?? documentData.amount_due ?? structured?.raw_totals?.amount_due;
  const taxRate = documentData.tax_rate ?? structured?.raw_totals?.tax_rate;
  const financialDifference = subtotal != null && lineItems.length > 0 ? Math.abs(Number(subtotal) - lineItemSum) : null;

  return (
    <DashboardLayout>
      <div className="doc-review-shell">
      <div className="doc-result-header doc-review-header">
        <div>
          <div className="section-label" style={{ marginBottom: 8 }}>§02 DOCUMENT INTELLIGENCE</div>
          <div className="doc-result-title serif">{processing?.document_type || documentRecord.document_type || "Document"}</div>
          <div className="doc-result-badges">
            <span className="badge badge-industry">{structured?.industry || "general"}</span>
            {!isProcessing && <span className="badge badge-done">✓ {processing?.status === "needs_review" ? "Review recommended" : "Ready"}</span>}
            <span className="badge" style={{ background: conf.bg, color: conf.color }}>{conf.label} confidence</span>
          </div>
        </div>
      </div>

      {workflowUnlocked && analysisReady && !isProcessing && (
        <section className={`doc-next-action${issues.length ? " needs-review" : ""}`} aria-label="Next safe action">
          <div>
            <span className="doc-next-action-eyebrow">Next safe action</span>
            <strong>{issues.length ? "Review the flagged details before moving this bill forward." : apStarted ? "AP processing is in progress." : "This bill is ready for AP processing."}</strong>
            <p>{issues.length ? `${issues.length} item${issues.length === 1 ? " needs" : "s need"} a decision. The original source is always available beside the extracted data.` : "No payment is created here. AP matching and approvals remain explicit next steps."}</p>
          </div>
          <div className="doc-next-action-buttons">
            {processing?.document_type === "invoice" && !apStarted && <button className="doc-action primary" onClick={runAP} disabled={runningAP}><Play size={14}/>{runningAP ? "Opening AP…" : "Continue to AP"}</button>}
            {issues.length > 0 && <button className="doc-action" onClick={() => setEditingCapture(true)}><Database size={14}/>Review data</button>}
            {apStarted && <Link className="doc-action primary" href={`/dashboard/document/${id}/ap-processing`}>Open AP workflow <ExternalLink size={14}/></Link>}
          </div>
        </section>
      )}

      {workflowUnlocked && !isProcessing && showAPMatching && (
        <APMatchingPanel
          invoiceId={id}
          vendorId={(documentRecord as any).vendor_id || (documentData as any).vendor_id || null}
          initialStatus={apStatus}
          onClose={() => setShowAPMatching(false)}
          onSaved={(status) => { setApStatus(status); setApStarted(Boolean(status.ap_status && status.ap_status !== "not_started")); }}
        />
      )}

      {isCapturing && (
        <div className="card" style={{ marginBottom: 16, padding: 22, border: "1px solid #E5E0D7" }}>
          <div className="section-card-header"><div><div className="section-card-name">Reading & recognizing document</div><div style={{ fontSize: 12, color: "#6B6860", marginTop: 4 }}>InvoiAI is extracting the fields needed for your History row. Full AI Analysis is not running.</div></div><span className="badge">{Math.max(0, Math.min(100, captureProgress))}%</span></div>
          <div style={{ height: 8, background: "#ECE7DE", borderRadius: 99, overflow: "hidden", marginTop: 16 }}><div style={{ height: "100%", width: `${Math.max(0, Math.min(100, captureProgress))}%`, background: "#C8922A", transition: "width .3s ease" }}/></div>
          <div className="muted" style={{ marginTop: 8 }}>{processing?.processing_message || "Reading the document and identifying its type…"}</div>
        </div>
      )}

      {isProcessing && <DocumentProcessingTimeline
        step={processing?.processing_step ?? undefined}
        message={processing?.processing_message ?? undefined}
        progress={processing?.processing_progress ?? undefined}
        failed={false}
      />}

      {isFailed && <div className="warning-box"><AlertTriangle size={16} color="#C0392B"/><div><div className="warning-title">Document Intelligence failed</div><p className="warning-text">{processing?.error_message || "InvoiAI could not finish the analysis."}</p></div></div>}

      {workflowUnlocked && !isProcessing && !analysisReady && !isFailed && (
        <div className="card" style={{ marginBottom: 16, padding: 24, border: "1px solid #DDE8DF" }}>
          <div className="section-card-header">
            <div>
              <div className="section-card-name">Document is ready</div>
              <div style={{ fontSize: 12, color: "#6B6860", marginTop: 4 }}>Recognition is complete. Choose what you want InvoiAI to do next.</div>
            </div>
            <span className="badge badge-done">✓ Captured</span>
          </div>
          <div className="doc-actions" style={{ marginTop: 18 }}>
            <button className="doc-action amber" onClick={() => void runAIAnalysis()} disabled={runningAnalysis || runningAP}><Play size={14}/>{runningAnalysis ? "Starting AI Analysis…" : "Run AI Analysis"}</button>
            {processing?.document_type === "invoice" && <button className="doc-action" onClick={runAP} disabled={runningAnalysis || runningAP}><Play size={14}/>Run AP Automation</button>}
            <button className="doc-action" onClick={() => setEditingCapture(true)}><Database size={14}/>Edit captured data</button>
          </div>
        </div>
      )}

      {captureReady && editingCapture && (
        <DocumentCaptureEditor
          documentId={id}
          documentData={{ ...documentData, ...processing, capture_overrides: processing?.capture_overrides || documentData?.capture_overrides || {} }}
          lineItems={lineItems as any[]}
          ocrFields={(workflow?.ocr?.key_value_pairs || {}) as Record<string, any>}
          sourceUrl={sourceUrl}
          sourceMimeType={sourceMimeType}
          documentType={processing?.document_type}
          currency={String(currency || "USD")}
          onCancel={() => setEditingCapture(false)}
          onSaved={async () => { setEditingCapture(false); await intelligence.refetch(); }}
        />
      )}

      {captureReady && !analysisReady && !editingCapture && (
        <div className="capture-editor" style={{ marginBottom: 18 }}>
          <div className="capture-editor-panel">
            <div className="capture-editor-head"><strong>Original document</strong><span className="badge">Source preserved</span></div>
            {sourceUrl ? (isImage ? <img src={sourceUrl} alt={text(source?.file_name, "Original document")} style={{ display: "block", width: "100%", maxHeight: 760, objectFit: "contain", background: "#F7F5F0" }} /> : isPdf ? <iframe src={sourceUrl} title="Original document" style={{ display: "block", width: "100%", height: 760, border: 0 }} /> : <div style={{ padding: 24 }} className="muted">{text(source?.file_name, processing?.file_name || "Original document")}</div>) : <div style={{ padding: 30 }} className="muted">Preparing the source preview…</div>}
          </div>
          <div className="capture-editor-panel">
            <div className="capture-editor-head"><strong>Extracted information</strong><button className="doc-action" onClick={() => setEditingCapture(true)}><Database size={13}/> Edit data</button></div>
            <div className="capture-editor-body">
              <div className="capture-field-grid">
                {[["Vendor", documentData.vendor_name], [processing?.document_type === "purchase_order" ? "PO number" : "Invoice number", documentData.document_number], ["Document date", formatDate(documentData.document_date)], ["Due date", formatDate(documentData.due_date)], ["Currency", currency], ["Payment terms", documentData.payment_terms], ["Subtotal", formatMoney(subtotal, currency)], ["Tax", formatMoney(taxAmount, currency)], ["Total", formatMoney(totalAmount, currency)], ["Amount due", formatMoney(amountDue ?? totalAmount, currency)], ["Account", processing?.gl_account_name || processing?.gl_account_code || processing?.capture_overrides?.gl_account_name || processing?.capture_overrides?.gl_account_code || "—"], ["Purchase order", processing?.capture_overrides?.purchase_order_number || "—"]].map(([label, value]) => <div className="capture-field" key={String(label)}><div className="capture-field-label"><span>{String(label)}</span></div><div className="capture-field-input" style={{ minHeight: 37 }}>{text(value)}</div></div>)}
              </div>
              {lineItems.length > 0 && <div style={{ marginTop: 18 }}><div className="section-card-name" style={{ marginBottom: 8 }}>Line items · {lineItems.length}</div><div className="capture-lines"><table className="section-table"><thead><tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr></thead><tbody>{lineItems.map((item, i) => <tr key={i}><td>{text(item.description)}</td><td>{text(item.quantity)}</td><td>{formatMoney(item.unit_price, currency)}</td><td>{formatMoney(item.amount, currency)}</td></tr>)}</tbody></table></div></div>}
              <div className="soft-notice" style={{ marginTop: 14 }}>Recognition is complete. This is the captured data used by History, Preview, and the next workflow you choose.</div>
            </div>
          </div>
        </div>
      )}

      {analysisReady && (
        <>
          <div className="card" style={{ marginBottom: 16, padding: 22, border: "1px solid #DDE8DF" }}>
            <div className="section-card-header">
              <div>
                <div className="section-card-name">Invoice workflow</div>
                <div style={{ fontSize: 12, color: "#6B6860", marginTop: 4 }}>Review → Process → Approve → Pay</div>
              </div>
              <span className="badge badge-done">✓ Captured · AI analyzed</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0,1fr))", gap: 8, margin: "18px 0" }}>
              {[
                ["1", "Review", isAccepted ? "done" : "current"],
                ["2", "Process", apStarted ? "current" : "locked"],
                ["3", "Approve", apStatus?.ap_status === "approved" ? "done" : "locked"],
                ["4", "Pay", apStatus?.payment_ready_at ? "done" : "locked"],
              ].map(([n, label, state]) => (
                <div key={label} style={{ padding: 12, borderRadius: 10, background: state === "locked" ? "#F7F5F0" : "#F1F7F2", border: "1px solid #E5E0D7" }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: state === "locked" ? "#8A857B" : "#3F6B4A" }}>{n} · {label}</div>
                  <div style={{ fontSize: 11, color: "#6B6860", marginTop: 4 }}>{state === "done" ? "Complete" : state === "current" ? "Current step" : "Unlocks next"}</div>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
              <div><div style={{ fontWeight: 700, fontSize: 14 }}>Document Intelligence complete</div><div style={{ fontSize: 12, color: "#6B6860", marginTop: 4 }}>The captured document has now been analyzed. AP Automation remains a separate explicit workflow.</div></div>
              <span className="badge badge-done">✓ Accepted · AI analyzed</span>
            </div>
          </div>

          <PaymentLifecyclePanel documentId={id} apStatus={apStatus?.ap_status} />

          <div className="doc-intelligence-grid">
            <div className="doc-intelligence-metric"><div className="doc-intelligence-metric-label">Health score</div><div className="doc-intelligence-metric-value">{score ?? "—"}/100</div><div className="risk-bar-label">{scoreLabel(score)}</div></div>
            <div className="doc-intelligence-metric"><div className="doc-intelligence-metric-label">Fraud / risk</div><div className="doc-intelligence-metric-value">{fraudAvailable ? `${fraud ?? "—"}/100` : "—"}</div><div className="risk-bar-label">{fraudAvailable ? scoreLabel(fraud) : "Not available"}</div></div>
            <div className="doc-intelligence-metric"><div className="doc-intelligence-metric-label">Financial checks</div><div className="doc-intelligence-metric-value">{financial ?? "—"}/100</div><div className="risk-bar-label">{scoreLabel(financial)}</div></div>
            <div className="doc-intelligence-metric"><div className="doc-intelligence-metric-label">Duplicate check</div><div className="doc-intelligence-metric-value">{duplicateAvailable ? `${duplicate ?? "—"}/100` : "—"}</div><div className="risk-bar-label">{!duplicateAvailable ? "Not available" : (analysis.is_duplicate || (duplicate ?? 100) < 70 ? "Review" : "Clear")}</div></div>
          </div>

          <div className="card" style={{ marginBottom: 16, padding: 20 }}>
            <div className="section-card-header"><div className="section-card-name">What InvoiAI found</div></div>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: "#575249", margin: "0 0 10px" }}>{analysis.summary || "InvoiAI completed its financial checks."}</p>
            {issues.length > 0 ? (
              <div className="doc-issue-list">{issues.map((issue, i) => <div key={i} className={`doc-issue ${issue.high ? "high" : ""}`}><div className="doc-issue-title"><ShieldAlert size={13} style={{ verticalAlign: "-2px", marginRight: 6 }}/>{issue.title}</div><div className="doc-issue-text">{issue.text}</div></div>)}</div>
            ) : <div className="soft-notice">✓ No major issues were flagged by the current analysis.</div>}
          </div>

          <div className="card" style={{ marginBottom: 16, padding: 20 }}>
            <div className="section-card-header"><div className="section-card-name">Original document</div><span className="badge">Source file preserved</span></div>
            <p style={{ fontSize: 12, color: "#6B6860", marginTop: 0 }}>Review the original invoice alongside the information InvoiAI extracted. This is the source used for OCR and verification.</p>
            {sourceUrl ? (
              <div style={{ border: "1px solid #E5E0D7", borderRadius: 12, overflow: "hidden", background: "#F7F5F0" }}>
                {isImage ? <img src={sourceUrl} alt={text(source?.file_name, "Original document")} style={{ display: "block", width: "100%", maxHeight: 900, objectFit: "contain", background: "#EEEAE2" }} /> : isPdf ? <iframe src={sourceUrl} title="Original document" style={{ display: "block", width: "100%", height: 900, border: 0 }} /> : <div style={{ padding: 28, display: "flex", alignItems: "center", gap: 12 }}><FileText size={24}/><div><div style={{ fontWeight: 600 }}>{text(source?.file_name, processing?.file_name || "Original document")}</div></div></div>}
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", padding: 12, borderTop: "1px solid #E5E0D7" }}>
                  <a href={sourceUrl} target="_blank" rel="noreferrer" className="doc-action" style={{ display: "inline-flex" }}>Open original document <ExternalLink size={14}/></a>
                  <a href={sourceUrl} download={source?.file_name || true} className="doc-action" style={{ display: "inline-flex" }}>Download original <Download size={14}/></a>
                </div>
              </div>
            ) : (
              <div className="soft-notice"><ImageIcon size={15} style={{ verticalAlign: "-3px", marginRight: 6 }}/>The original document preview is not available right now, but the stored source file is still associated with this document.</div>
            )}
          </div>

          <div className="card" style={{ marginBottom: 16, padding: 20 }}>
            <div className="section-card-header"><div className="section-card-name">Extracted information</div><div className="doc-actions"><button className="doc-action" onClick={() => setEditingCapture(true)}><Database size={13}/> Edit data</button><span className="badge">Human-readable</span></div></div>
            <div className="kv-row"><span className="kv-key">Vendor</span><span className="kv-val">{text(documentData.vendor_name ?? processing?.vendor_name ?? documentRecord.vendor_name)}</span></div>
            <div className="kv-row"><span className="kv-key">Invoice number</span><span className="kv-val">{text(documentData.document_number ?? processing?.document_number ?? documentRecord.document_number)}</span></div>
            <div className="kv-row"><span className="kv-key">Document date</span><span className="kv-val">{formatDate(documentData.document_date ?? processing?.document_date ?? documentRecord.document_date)}</span></div>
            <div className="kv-row"><span className="kv-key">Due date</span><span className="kv-val">{formatDate(documentData.due_date ?? processing?.due_date ?? documentRecord.due_date)}</span></div>
            <div className="kv-row"><span className="kv-key">Currency</span><span className="kv-val">{currency ? text(currency) : "Missing — review the original document"}</span></div>
            <div className="kv-row"><span className="kv-key">Payment terms</span><span className="kv-val">{text(documentData.payment_terms ?? processing?.payment_terms)}</span></div>
            <div className="kv-row"><span className="kv-key">Payment method</span><span className="kv-val">{text(documentData.payment_method ?? processing?.payment_method)}</span></div>
          </div>

          <details className="doc-supporting-evidence">
            <summary>Supporting extraction and OCR evidence</summary>
            <p>Use these details when you need to verify a field or understand how InvoiAI reached its result.</p>
            <div className="doc-evidence-actions">
              <button className="doc-action" onClick={() => downloadExcel(id)} disabled={isDownloadingExcel}><Download size={14}/>{isDownloadingExcel ? "Preparing…" : "Download Excel"}</button>
              <button className="doc-action" onClick={() => downloadCsv(id)} disabled={isDownloadingCsv}><Download size={14}/>{isDownloadingCsv ? "Preparing…" : "Download CSV"}</button>
              <button className="doc-action" onClick={() => exportToSheets(id)} disabled={isExportingToSheets}><ExternalLink size={14}/>{isExportingToSheets ? "Exporting…" : "Export to Sheets"}</button>
            </div>
          {Object.entries(structured.sections ?? {})
            .filter(([name]) => name !== "document" && name !== "ocr_captured_fields" && name !== "line_items")
            .map(([name, sectionData]) => (
              <div className="card section-card" key={name} style={{ marginBottom: 16 }}>
                <div className="section-card-header"><div className="section-card-name">{labelize(name)}</div><span className="badge">Extracted</span></div>
                {Array.isArray(sectionData) ? (
                  sectionData.length > 0 && isRecord(sectionData[0]) ? (
                    <div style={{ overflowX: "auto" }}><table className="section-table"><thead><tr>{Object.keys(sectionData[0]).map((key) => <th key={key}>{labelize(key)}</th>)}</tr></thead><tbody>{sectionData.map((row, index) => <tr key={index}>{isRecord(row) ? Object.values(row).map((value, cell) => <td key={cell}>{humanValue(value)}</td>) : <td colSpan={Object.keys(sectionData[0] as Record<string, unknown>).length}>{humanValue(row)}</td>}</tr>)}</tbody></table></div>
                  ) : (
                    <div>{sectionData.map((value, index) => <div className="kv-row" key={index}><span className="kv-key">Item {index + 1}</span><span className="kv-val">{humanValue(value)}</span></div>)}</div>
                  )
                ) : isRecord(sectionData) ? (
                  <div>{Object.entries(sectionData).map(([key, value]) => <div className="kv-row" key={key}><span className="kv-key">{labelize(key)}</span><span className="kv-val">{humanValue(value)}</span></div>)}</div>
                ) : (
                  <div className="kv-row"><span className="kv-key">Value</span><span className="kv-val">{humanValue(sectionData)}</span></div>
                )}
              </div>
            ))}

          <div className="card" style={{ marginBottom: 16, padding: 20 }}>
            <div className="section-card-header"><div className="section-card-name">Financial summary</div><span className="badge">{financialDifference != null && financialDifference <= 0.01 ? "✓ Calculated correctly" : "Review"}</span></div>
            <div className="doc-intelligence-grid" style={{ margin: 0 }}>
              <div className="doc-intelligence-metric"><div className="doc-intelligence-metric-label">Subtotal</div><div className="doc-intelligence-metric-value" style={{ fontSize: 22 }}>{formatMoney(subtotal, currency)}</div></div>
              <div className="doc-intelligence-metric"><div className="doc-intelligence-metric-label">Tax {taxRate != null ? `(${Number(taxRate) <= 1 ? Number(taxRate) * 100 : Number(taxRate)}%)` : ""}</div><div className="doc-intelligence-metric-value" style={{ fontSize: 22 }}>{formatMoney(taxAmount, currency)}</div></div>
              <div className="doc-intelligence-metric"><div className="doc-intelligence-metric-label">Total</div><div className="doc-intelligence-metric-value" style={{ fontSize: 22 }}>{formatMoney(totalAmount, currency)}</div></div>
              <div className="doc-intelligence-metric"><div className="doc-intelligence-metric-label">Amount due</div><div className="doc-intelligence-metric-value" style={{ fontSize: 22 }}>{formatMoney(amountDue ?? totalAmount, currency)}</div></div>
            </div>
            {financialDifference != null && <div className="soft-notice" style={{ marginTop: 14 }}>Line items add up to {formatMoney(lineItemSum, currency)}{financialDifference <= 0.01 ? " — matching the captured subtotal." : ` — ${formatMoney(financialDifference, currency)} different from the captured subtotal.`}</div>}
          </div>

          {lineItems.length > 0 && <div className="card" style={{ marginBottom: 16, padding: 20 }}><div className="section-card-header"><div className="section-card-name">Invoice items</div><span className="badge">{lineItems.length} item{lineItems.length === 1 ? "" : "s"}</span></div><div style={{ overflowX: "auto" }}><table className="section-table"><thead><tr><th>Item</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr></thead><tbody>{lineItems.map((item, i) => <tr key={i}><td>{text(item.description)}</td><td>{text(item.quantity)}</td><td>{formatMoney(item.unit_price, currency)}</td><td>{formatMoney(item.amount, currency)}</td></tr>)}</tbody></table></div></div>}

          <div className="card" style={{ marginBottom: 16, padding: 20 }}>
            <div className="section-card-header"><div className="section-card-name">Financial memory</div></div>
            <div className="kv-row"><span className="kv-key">Vendor record</span><span className="kv-val">{vendor?.name || documentData.vendor_name || documentRecord.vendor_name || "Not resolved"}</span></div>
            <div className="kv-row"><span className="kv-key">Vendor risk</span><span className="kv-val">{vendor?.risk_score != null ? `${vendor.risk_score}/100 · ${vendor.risk_level || ""}` : "Not available"}</span></div>
            <div className="kv-row"><span className="kv-key">Document embedding</span><span className="kv-val">{workflow?.embedding ? `Ready · ${workflow.embedding.model_used || "semantic memory"}` : "Pending"}</span></div>
            <div className="kv-row"><span className="kv-key">Vendor embedding</span><span className="kv-val">{workflow?.vendor_embedding_ready ? "Ready" : vendor ? "Building" : "Not applicable"}</span></div>
          </div>

          <div className="card" style={{ marginBottom: 16, padding: 20 }}>
            <div className="section-card-header"><div className="section-card-name">OCR captured information</div><span className="badge">Human-readable</span></div>
            <div className="kv-row"><span className="kv-key">OCR engine</span><span className="kv-val">{humanValue(workflow.ocr?.engine, "AI OCR")} {humanValue(workflow.ocr?.engine_version, "")}</span></div>
            <div className="kv-row"><span className="kv-key">OCR confidence</span><span className="kv-val">{workflow.ocr?.confidence_score != null ? `${Math.round(Number(workflow.ocr.confidence_score) * 100)}%` : "—"}</span></div>
            <div className="kv-row"><span className="kv-key">Pages read</span><span className="kv-val">{humanValue(workflow.ocr?.page_count)}</span></div>
            <div className="kv-row"><span className="kv-key">Language</span><span className="kv-val">{humanValue(workflow.ocr?.language_detected)}</span></div>
            <div className="kv-row"><span className="kv-key">Tables detected</span><span className="kv-val">{workflow.ocr?.has_tables == null ? "—" : workflow.ocr.has_tables ? "Yes" : "No"}</span></div>
            {isRecord(workflow.ocr?.key_value_pairs) && Object.entries(workflow.ocr.key_value_pairs).map(([key, value]) => (
              <div className="kv-row" key={key}><span className="kv-key">{labelize(key)}</span><span className="kv-val">{capturedValue(key, value)}</span></div>
            ))}
            <details style={{ marginTop: 14 }}>
              <summary style={{ cursor: "pointer", fontWeight: 600 }}>Read OCR text</summary>
              <div style={{ marginTop: 10, padding: 14, borderRadius: 10, background: "#F7F5F0", whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.7, color: "#403D37" }}>
                {rawOcrText || "No OCR text was returned."}
              </div>
            </details>
          </div>
          </details>
        </>
      )}

      {processing?.status === "failed" && <div className="warning-box"><AlertTriangle size={16} color="#C0392B"/><div><div className="warning-title">Processing stopped</div><p className="warning-text">{processing.error_message || "InvoiAI could not finish this document."}</p></div></div>}

      <div id="document-data">
        {warnings.length > 0 && <div className="warning-box"><AlertTriangle size={16} color="#C8922A"/><div><div className="warning-title">Items to review</div>{warnings.map((warning, i) => <p key={i} className="warning-text">• {friendlyIssueText(String(warning), documentData)}</p>)}</div></div>}
        <div className="card" style={{ marginBottom: 16, padding: 20 }}><div className="export-panel"><div className="export-panel-label">Document overview</div><div className="export-buttons"><span className="badge">{workflow?.ocr?.page_count ?? "—"} pages</span><span className="badge">OCR {workflow?.ocr?.confidence_score != null ? `${Math.round(Number(workflow.ocr.confidence_score) * 100)}%` : "complete"}</span><span className="badge">{workflow?.ocr?.engine || "AI OCR"}</span><span className="badge">{text(processing?.file_name || documentRecord.file_name)}</span></div></div></div>
      </div>
      </div>
    </DashboardLayout>
  );
}
