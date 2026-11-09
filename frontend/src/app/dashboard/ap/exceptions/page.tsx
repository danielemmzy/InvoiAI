"use client";

import { useState } from "react";
import Link from "next/link";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useAPExceptions } from "@/hooks/useAP";
import { AlertTriangle, ArrowRight, Check, CheckCircle2, FileText, Loader2, ShieldCheck } from "lucide-react";
import { apApi, APException } from "@/api/ap";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getErrorMessage } from "@/api/client";

function money(value?: number | string | null, currency?: string | null) {
  if (value == null || value === "") return "Amount unavailable";
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  try { return new Intl.NumberFormat(undefined, { style: "currency", currency: currency || "USD", maximumFractionDigits: 2 }).format(n); }
  catch { return `${currency || ""} ${n.toLocaleString()}`.trim(); }
}

export default function ExceptionsPage() {
  const q = useAPExceptions();
  const qc = useQueryClient();
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<Record<string, "resolve" | "waive" | undefined>>({});

  async function act(exception: APException, waive = false) {
    const note = (notes[exception.id] || "").trim();
    if (waive && !note) { toast.error("Add a reason before waiving an exception."); return; }
    setBusy((state) => ({ ...state, [exception.id]: waive ? "waive" : "resolve" }));
    try {
      if (waive) await apApi.waiveException(exception.id, note);
      else await apApi.resolveException(exception.id, note || "Underlying issue corrected by reviewer; revalidation requested.");
      await qc.invalidateQueries({ queryKey: ["ap-exceptions"] });
      await qc.invalidateQueries({ queryKey: ["ap-status"] });
      toast.success(waive ? "Exception waived with a recorded reason." : "Exception resolved. The invoice workflow is rechecking the affected step.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not update this exception."));
    } finally {
      setBusy((state) => ({ ...state, [exception.id]: undefined }));
    }
  }

  function invoiceHref(exception: APException) {
    const returnTo = typeof window === "undefined" ? "/dashboard/ap/exceptions" : `${window.location.pathname}${window.location.search}`;
    return `/dashboard/document/${exception.document_id}?returnTo=${encodeURIComponent(returnTo)}&returnLabel=AP%20exceptions`;
  }

  return (
    <DashboardLayout>
      <div className="page-head">
        <div><div className="eyebrow">Accounts payable</div><h1 className="page-title">Exceptions</h1><p className="page-subtitle">Every exception is linked to its source invoice. Resolve after correcting the issue; waive only when an authorized reviewer accepts the documented risk.</p></div>
      </div>
      {q.isLoading ? <div className="loading-state"><Loader2 className="spin" />Loading exceptions…</div> : q.isError ? <div className="soft-notice"><AlertTriangle size={17} />Couldn’t load exceptions. Refresh and try again.</div> : (q.data ?? []).length === 0 ? <div className="panel empty-state"><CheckCircle2 size={24} /><h3>Everything is clear.</h3><p>No open AP exceptions need a decision.</p></div> : (
        <div style={{ display: "grid", gap: 14 }}>
          {(q.data ?? []).map((exception) => {
            const doc = exception.document;
            const isBusy = !!busy[exception.id];
            const title = exception.title || exception.exception_type.replaceAll("_", " ");
            const description = exception.description || exception.message || "This invoice needs review before AP processing can continue.";
            const isCoding = exception.exception_type === "gl_coding_required";
            return <article className="panel" key={exception.id} style={{ padding: 22, border: "1px solid #E5E0D7", borderRadius: 16 }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 14, flexWrap: "wrap" }}>
                <div style={{ minWidth: 240, flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}><span className={`severity ${exception.severity || "warning"}`}>{exception.severity || "review"}</span><span className="badge">{exception.status.replaceAll("_", " ")}</span></div>
                  <h3 style={{ margin: "12px 0 6px", textTransform: "capitalize" }}>{title}</h3><p style={{ margin: 0, color: "#6B6860", lineHeight: 1.6, fontSize: 13 }}>{description}</p>
                  {(exception.expected_value || exception.actual_value || exception.variance) && <div className="soft-notice" style={{ marginTop: 12, display: "flex", gap: 16, flexWrap: "wrap" }}>{exception.expected_value && <span>Expected: <strong>{exception.expected_value}</strong></span>}{exception.actual_value && <span>Actual: <strong>{exception.actual_value}</strong></span>}{exception.variance && <span>Variance: <strong>{exception.variance}</strong></span>}</div>}
                </div>
                <div style={{ minWidth: 250, padding: 14, background: "#F8F6F1", borderRadius: 12, border: "1px solid #EAE6DE" }}>
                  <div style={{ display: "flex", gap: 9, alignItems: "flex-start" }}><FileText size={18} color="#8A6B2F" /><div><div style={{ fontWeight: 700 }}>{doc?.document_number || doc?.file_name || `Invoice ${exception.document_id.slice(0, 8)}`}</div><div style={{ color: "#6B6860", fontSize: 12, marginTop: 4 }}>{doc?.vendor_name || "Vendor unavailable"}</div><div style={{ color: "#6B6860", fontSize: 12, marginTop: 4 }}>{money(doc?.total_amount, doc?.currency)}</div></div></div>
                  <Link href={invoiceHref(exception)} className="doc-action" style={{ display: "inline-flex", marginTop: 12, width: "100%", justifyContent: "center" }}>Review source invoice <ArrowRight size={14} /></Link>
                </div>
              </div>
              <label style={{ display: "block", marginTop: 16, fontSize: 12, fontWeight: 700, color: "#575249" }}>{exception.resolution_note ? "Previous resolution note" : "Resolution / waiver note"}
                <input value={notes[exception.id] ?? ""} onChange={(e) => setNotes((state) => ({ ...state, [exception.id]: e.target.value }))} className="ap-filter-select" style={{ display: "block", width: "100%", marginTop: 7, padding: "10px 12px" }} placeholder={isCoding ? "Describe the GL coding correction…" : "Explain what was corrected; required for waiver"} />
              </label>
              {isCoding && <div className="soft-notice" style={{ marginTop: 10 }}>GL coding exceptions must be corrected by assigning a valid account to each affected invoice line. They cannot be waived.</div>}
              <div style={{ display: "flex", gap: 9, justifyContent: "flex-end", flexWrap: "wrap", marginTop: 15 }}>
                <button className="btn-secondary" disabled={isBusy} onClick={() => void act(exception, false)}>{busy[exception.id] === "resolve" ? <Loader2 size={14} className="spin" /> : <Check size={14} />} Resolve & recheck</button>
                {!isCoding && <button className="btn-quiet" disabled={isBusy} onClick={() => void act(exception, true)}>{busy[exception.id] === "waive" ? <Loader2 size={14} className="spin" /> : <ShieldCheck size={14} />} Waive with reason</button>}
              </div>
            </article>;
          })}
        </div>
      )}
    </DashboardLayout>
  );
}
