"use client";
// Upload — /dashboard/upload
//
// Used to be single-file only (maxFiles:1 hardcoded, no batch endpoint
// existed on the backend). Now supports selecting several files at once,
// capped by the workspace's plan (see core/plan.py max_batch_upload —
// enforced server-side too, this is just the UI reflecting the same
// number so people aren't surprised by a 400 after the fact).

import { useCallback, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import Link from "next/link";
import { FileText, ReceiptText, FileStack, ScanLine, X, Loader2, CheckCircle2, AlertTriangle, Upload as UploadIcon } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useUpload, useBatchUpload } from "@/hooks/useUpload";
import { useIndustries } from "@/hooks/useDocuments";
import { usePlanCatalog } from "@/hooks/useBilling";
import { useAppStore } from "@/store/useAppStore";

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [industry, setIndustry] = useState("general");
  const { data: industries } = useIndustries();
  const { data: plans } = usePlanCatalog();
  const user = useAppStore((s) => s.user);

  const currentPlan = plans?.find((p) => p.id === (user?.plan || "free"));
  const batchLimit = currentPlan?.max_batch_upload ?? 1;

  const { upload, isUploading: isSingleUploading } = useUpload();
  const { uploadBatch, isUploading: isBatchUploading, result, reset } = useBatchUpload();
  const isUploading = isSingleUploading || isBatchUploading;

  const onDrop = useCallback(
    (accepted: File[]) => {
      reset();
      setFiles((prev) => {
        const combined = [...prev, ...accepted];
        if (combined.length > batchLimit) {
          return combined.slice(0, batchLimit);
        }
        return combined;
      });
    },
    [batchLimit, reset]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/webp": [".webp"],
    },
    maxFiles: batchLimit,
    disabled: isUploading,
  });

  const removeFile = (idx: number) => setFiles((prev) => prev.filter((_, i) => i !== idx));
  const atLimit = files.length >= batchLimit;

  function handleSend() {
    if (!files.length) return;
    if (files.length === 1) {
      upload({ file: files[0], industry, documentType: "unknown" });
    } else {
      uploadBatch({ files, industry });
    }
  }

  const totalSizeMb = useMemo(() => files.reduce((sum, f) => sum + f.size, 0) / 1024 / 1024, [files]);

  return (
    <DashboardLayout>
      <div style={{ maxWidth: 760 }}>
        <div className="section-label">§01 Intake / Universal document inbox</div>
        <div className="dash-title serif">Send InvoiAI anything.</div>
        <div className="dash-subtitle" style={{ marginBottom: 24 }}>
          Invoices, receipts, purchase orders, delivery notes, contracts and other documents are
          classified automatically. Upload up to {batchLimit} at once on your {currentPlan?.display_name || "current"} plan.
        </div>

        <div className="dash-grid" style={{ marginBottom: 18 }}>
          {[[FileText, "Invoice / AP"], [ReceiptText, "Receipt / Expense"], [FileStack, "PO / Procurement"], [ScanLine, "Other documents"]].map(([Icon, title]: any) => (
            <div className="card" style={{ padding: 18 }} key={title}>
              <Icon size={20} />
              <div className="card-title" style={{ marginTop: 10 }}>{title}</div>
              <div className="dash-subtitle" style={{ fontSize: 12 }}>AI routes it to the right workflow.</div>
            </div>
          ))}
        </div>

        <div {...getRootProps()} className={`upload-dropzone${isDragActive ? " active" : ""}${files.length ? " has-file" : ""}${atLimit ? " at-limit" : ""}`}>
          <input {...getInputProps()} />
          {files.length === 0 ? (
            <>
              <div className="upload-icon-wrap"><UploadIcon size={20} /></div>
              <div className="upload-title">{isDragActive ? "Drop them here" : "Drop up to " + batchLimit + " documents here"}</div>
              <div className="upload-sub">PDF, JPG, PNG or WEBP · up to 10MB each</div>
              <div className="upload-browse">or click to browse files</div>
            </>
          ) : (
            <div className="upload-file-list" onClick={(e) => e.stopPropagation()}>
              {files.map((f, idx) => (
                <div key={`${f.name}-${idx}`} className="upload-file-row">
                  <FileText size={16} />
                  <div className="upload-file-row-info">
                    <div className="upload-file-row-name">{f.name}</div>
                    <div className="upload-file-row-size">{(f.size / 1024 / 1024).toFixed(2)} MB</div>
                  </div>
                  {!isUploading && (
                    <button className="file-remove" onClick={() => removeFile(idx)} aria-label={`Remove ${f.name}`}>
                      <X size={12} />
                    </button>
                  )}
                </div>
              ))}
              {!atLimit && !isUploading && (
                <button
                  className="upload-add-more"
                  onClick={(e) => { e.stopPropagation(); (document.querySelector(".upload-dropzone input") as HTMLInputElement)?.click(); }}
                >
                  + Add more (up to {batchLimit - files.length} more)
                </button>
              )}
              {atLimit && (
                <div className="upload-limit-note">
                  Reached your {currentPlan?.display_name || "plan"} limit of {batchLimit} files per upload.
                  {" "}<Link href="/dashboard/billing">Upgrade for a higher limit →</Link>
                </div>
              )}
            </div>
          )}
        </div>

        {files.length > 0 && (
          <div className="upload-summary-bar">
            <span>{files.length} file{files.length === 1 ? "" : "s"} · {totalSizeMb.toFixed(1)} MB total</span>
            <button className="upload-clear-all" onClick={() => setFiles([])} disabled={isUploading}>Clear all</button>
          </div>
        )}

        <label className="form-label" style={{ display: "block", marginTop: 16 }}>Industry context (optional)</label>
        <select className="finance-input" value={industry} onChange={(e) => setIndustry(e.target.value)}>
          <option value="general">General</option>
          {(industries || []).map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
        </select>

        <button
          onClick={handleSend}
          disabled={!files.length || isUploading}
          className="btn-primary"
          style={{ width: "100%", marginTop: 18, justifyContent: "center", padding: 14 }}
        >
          {isUploading ? (
            <><Loader2 size={16} className="animate-spin" /> Receiving {files.length > 1 ? `${files.length} files` : ""}…</>
          ) : (
            `Send ${files.length > 1 ? `${files.length} documents` : "to InvoiAI"} →`
          )}
        </button>

        {/* Per-file batch result */}
        {result && (
          <div className="card" style={{ padding: 18, marginTop: 18 }}>
            <b>{result.accepted} of {result.total} received</b>
            <div className="upload-result-list">
              {result.results.map((r) => (
                <div key={r.filename} className={`upload-result-row ${r.status}`}>
                  {r.status === "accepted" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                  <span className="upload-result-name">{r.filename}</span>
                  {r.status === "error" && <span className="upload-result-error">{r.error}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="card" style={{ padding: 18, marginTop: 18 }}>
          <b>Processing pipeline</b>
          <div className="dash-subtitle" style={{ marginTop: 6 }}>
            Security → duplicate detection → OCR → AI classification → workflow routing.
            Processing continues in the background for every file in a batch independently.
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
