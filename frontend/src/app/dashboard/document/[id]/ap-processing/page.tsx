"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, ArrowRight, CheckCircle2, Circle, Clock3, Loader2, Send, ShieldCheck } from "lucide-react";
import toast from "react-hot-toast";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { APStatus, apApi } from "@/api/ap";
import { getErrorMessage } from "@/api/client";
import GLCodingPanel from "@/components/ap/GLCodingPanel";

const FINAL = new Set(["awaiting_approval", "approved", "rejected", "payment_ready", "paid", "reconciled"]);

export default function APProcessingPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const invoiceId = String(params.id || "");
  const [status, setStatus] = useState<APStatus | null>(null);
  const [lineItems, setLineItems] = useState<Array<{
    id: string;
    description?: string | null;
    quantity?: number | null;
    unit_price?: number | null;
    amount?: number | null;
    gl_account_id?: string | null;
    gl_account_code?: string | null;
    gl_account_name?: string | null;
  }>>([]);
  const [loading, setLoading] = useState(true);
  const [connectionIssue, setConnectionIssue] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const refresh = useCallback(async () => {
    if (!invoiceId) return null;
    const [next, items] = await Promise.all([
      apApi.getStatus(invoiceId),
      apApi.getCodings(invoiceId).then(() => apApi.getCodings(invoiceId)).catch(() => []).then(async () => {
        // Fetch line items from the document
        try {
          const doc = await apApi.getCodings(invoiceId);
          // Actually we need a different endpoint for line items
          // For now, let's use the status endpoint which might have line items or fetch from documents
          return [] as any[];
        } catch {
          return [] as any[];
        }
      }),
    ]);
    setStatus(next);
    setConnectionIssue(false);
    return next;
  }, [invoiceId]);

  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const next = await apApi.getStatus(invoiceId);
        if (disposed) return;
        setStatus(next);
        setConnectionIssue(false);
        setLoading(false);
        if (!FINAL.has(String(next.ap_status))) {
          const delay = ["match_exception", "coding_exception", "on_hold"].includes(String(next.ap_status)) ? 7000 : 3500;
          timer = setTimeout(poll, delay);
        }
      } catch {
        if (disposed) return;
        setConnectionIssue(true);
        setLoading(false);
        timer = setTimeout(poll, 5000);
      }
    };
    void poll();
    return () => { disposed = true; if (timer) clearTimeout(timer); };
  }, [invoiceId]);

  const submit = async () => {
    setSubmitting(true);
    try {
      await apApi.submitForApproval(invoiceId);
      toast.success("Invoice submitted to the approval workflow.");
      const next = await refresh();
      if (next?.ap_status === "awaiting_approval" || next?.ap_status === "approved") {
        router.push(`/dashboard/approvals`);
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not submit this invoice for approval."));
      try { await refresh(); } catch { /* polling will retry */ }
    } finally {
      setSubmitting(false);
    }
  };

  const apState = String(status?.ap_status || "validating");
  const exceptionState = ["match_exception", "coding_exception", "on_hold"].includes(apState);
  const readyToSubmit = apState === "coding" && ["auto_coded", "approved"].includes(String(status?.gl_coding_status));
  const currentStage = apState === "awaiting_approval" || apState === "approved" || apState === "rejected" || apState === "payment_ready" || apState === "paid" || apState === "reconciled" ? 3 : apState === "coding" || apState === "coding_exception" ? 2 : 1;
  const stages = [
    { title: "Validate invoice", detail: "Confirm invoice fields and matching context", step: 1 },
    { title: "Match and assign GL accounts", detail: "Compare the invoice and code each line item", step: 2 },
    { title: "Send for approval", detail: "Submit the completed invoice to the approval workflow", step: 3 },
  ];

  return (
    <DashboardLayout>
      <div className="page-head" style={{ alignItems: "flex-start", gap: 20 }}>
        <div>
          <div className="eyebrow">Accounts payable · Invoice workflow</div>
          <h1 className="page-title">AP processing</h1>
          <p className="page-subtitle">Track matching and coding here. Payment is not made by submitting an invoice for approval.</p>
        </div>
        <span className="badge" style={{ padding: "9px 12px", borderRadius: 999 }}>{apState.replaceAll("_", " ")}</span>
      </div>

      <section className="panel" style={{ padding: 24, marginBottom: 18, border: "1px solid #E5E0D7", borderRadius: 18 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <div className="section-card-name">Processing progress</div>
            <p style={{ margin: "8px 0 0", color: "#6B6860", fontSize: 13 }}>Invoice reference · {invoiceId.slice(0, 8)}</p>
          </div>
          <strong style={{ fontSize: 24, color: "#3F6B4A" }}>{Math.max(0, Math.min(100, Number(status?.processing_progress ?? 5)))}%</strong>
        </div>
        <div style={{ height: 9, background: "#EEEAE2", borderRadius: 999, overflow: "hidden", marginTop: 18 }}>
          <div style={{ height: "100%", width: `${Math.max(0, Math.min(100, Number(status?.processing_progress ?? 5)))}%`, background: exceptionState ? "#C8922A" : "#477453", borderRadius: 999, transition: "width .35s ease" }} />
        </div>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginTop: 15, color: "#4E4A42", lineHeight: 1.6 }}>
          {loading ? <Loader2 className="spin" size={18} /> : exceptionState ? <AlertTriangle size={18} color="#B7791F" /> : readyToSubmit ? <ShieldCheck size={18} color="#477453" /> : <Clock3 size={18} />}
          <div>
            <strong>{status?.processing_step?.replaceAll("_", " ") || (loading ? "Loading AP status" : "AP workflow")}</strong>
            <div style={{ fontSize: 13, marginTop: 3 }}>{status?.processing_message || (loading ? "Checking the latest workflow status…" : "Waiting for the next workflow update.")}</div>
          </div>
        </div>
        {connectionIssue && <div className="soft-notice" style={{ marginTop: 14 }}><AlertTriangle size={15} style={{ verticalAlign: "-3px", marginRight: 6 }} />Status refresh is temporarily unavailable. The page will retry automatically; this does not cancel the AP job.</div>}
      </section>

      <section className="panel" style={{ padding: 22, marginBottom: 18, borderRadius: 18 }}>
        <div className="section-card-name" style={{ marginBottom: 18 }}>Workflow stages</div>
        <div style={{ display: "grid", gap: 14 }}>
          {stages.map((stage) => {
            const done = stage.step < currentStage || (stage.step === 2 && readyToSubmit) || (stage.step === 3 && ["awaiting_approval", "approved", "payment_ready", "paid", "reconciled"].includes(apState));
            const current = !done && stage.step === currentStage && !exceptionState;
            return <div key={stage.step} style={{ display: "flex", gap: 13, alignItems: "flex-start", padding: 15, border: `1px solid ${done ? "#D6E6D8" : current ? "#DCCFAE" : "#EAE6DE"}`, borderRadius: 14, background: done ? "#F5FAF5" : current ? "#FFFCF5" : "#FFFFFF" }}>
              <div style={{ marginTop: 1, color: done ? "#477453" : current ? "#B7791F" : "#A7A197" }}>{done ? <CheckCircle2 size={20} /> : current ? <Loader2 className="spin" size={20} /> : <Circle size={20} />}</div>
              <div style={{ flex: 1 }}><div style={{ fontWeight: 700 }}>{stage.title}{current ? " · In progress" : !done ? " · Next" : " · Complete"}</div><div style={{ fontSize: 13, color: "#6B6860", marginTop: 4 }}>{stage.detail}</div></div>
            </div>;
          })}
        </div>
      </section>

      {exceptionState && <section className="warning-box" style={{ marginBottom: 18 }}><AlertTriangle size={18} color="#B7791F" /><div style={{ flex: 1 }}><div className="warning-title">An exception needs attention</div><p className="warning-text">{status?.processing_message || "Review the invoice-specific exception and correct the underlying issue. Returning here reloads the saved workflow state."}</p><Link className="doc-action" style={{ display: "inline-flex", marginTop: 8 }} href={`/dashboard/document/${invoiceId}?returnTo=${encodeURIComponent(`/dashboard/document/${invoiceId}/ap-processing`)}&returnLabel=AP%20processing`}>Open invoice to correct GL coding <ArrowRight size={14} /></Link><Link className="doc-action primary" style={{ display: "inline-flex", marginTop: 8 }} href={`/dashboard/ap/exceptions?returnTo=${encodeURIComponent(`/dashboard/document/${invoiceId}/ap-processing`)}&returnLabel=AP%20processing`}>Review AP exceptions <ArrowRight size={14} /></Link></div></section>}

      {readyToSubmit && <section className="panel" style={{ padding: 22, borderRadius: 18, border: "1px solid #D6E6D8", background: "#F8FCF8" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}><div><div className="section-card-name">Ready for approval</div><p style={{ margin: "7px 0 0", fontSize: 13, color: "#5E625A", lineHeight: 1.6 }}>Matching and GL coding have finished. Review the invoice and submit it to the approval workflow when you are ready. No payment is initiated here.</p></div><button className="doc-action primary" onClick={() => void submit()} disabled={submitting}>{submitting ? <Loader2 className="spin" size={15} /> : <Send size={15} />}{submitting ? "Submitting…" : "Submit for approval"}</button></div>
      </section>}

      {apState === "awaiting_approval" && <section className="panel" style={{ padding: 22, borderRadius: 18 }}><div className="section-card-name">Submitted for approval</div><p style={{ color: "#6B6860", fontSize: 13 }}>The invoice is now in the approval queue. Payment remains a separate later step.</p><Link className="doc-action primary" href="/dashboard/approvals" style={{ display: "inline-flex" }}>Open approvals <ArrowRight size={14} /></Link></section>}
      {FINAL.has(apState) && <section className="panel" style={{ padding: 22, borderRadius: 18 }}><div className="section-card-name">AP status: {apState.replaceAll("_", " ")}</div><p style={{ color: "#6B6860", fontSize: 13 }}>{status?.processing_message || "The workflow has reached a later state."}</p><Link className="doc-action" href={`/dashboard/document/${invoiceId}`}>Return to invoice</Link></section>}
    </DashboardLayout>
  );
}
