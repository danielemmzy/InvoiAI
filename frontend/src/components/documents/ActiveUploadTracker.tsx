"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle2, ChevronRight, Loader2, X, XCircle } from "lucide-react";
import { useQueries } from "@tanstack/react-query";
import { documentsApi } from "@/api/documents";
import { useAppStore } from "@/store/useAppStore";

const KEY = "invoiai-active-document-ids";
const DISMISSED_KEY = "invoiai-dismissed-document-notifications";

export default function ActiveUploadTracker() {
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  const [ids, setIds] = useState<string[]>([]);

  const readIds = () => {
    try {
      const active = JSON.parse(localStorage.getItem(KEY) || "[]");
      const dismissed = JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]");
      const dismissedSet = new Set<string>(Array.isArray(dismissed) ? dismissed : []);
      return (Array.isArray(active) ? active : []).filter((id): id is string => typeof id === "string" && !dismissedSet.has(id));
    } catch {
      return [];
    }
  };

  const dismiss = (id: string) => {
    try {
      const dismissed = JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]");
      const next = Array.from(new Set([...(Array.isArray(dismissed) ? dismissed : []), id]));
      localStorage.setItem(DISMISSED_KEY, JSON.stringify(next));
      setIds((current) => current.filter((currentId) => currentId !== id));
    } catch {
      setIds((current) => current.filter((currentId) => currentId !== id));
    }
  };

  useEffect(() => {
    if (typeof window === "undefined") return;
    setIds(readIds());
    const onStorage = () => setIds(readIds());
    window.addEventListener("storage", onStorage);
    const timer = window.setInterval(onStorage, 2000);
    return () => { window.removeEventListener("storage", onStorage); window.clearInterval(timer); };
  }, []);

  const queries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["upload-tracker", ws, id],
      queryFn: () => documentsApi.getIntelligence(id),
      enabled: !!ws,
      refetchInterval: (q: any) => {
        const d = q.state.data?.document;
        const intelligenceStatus = String(d?.intelligence_status || "not_requested").toLowerCase();
        const step = String(d?.processing_step || "").toLowerCase();
        const terminal =
          intelligenceStatus === "not_requested" ||
          intelligenceStatus === "complete" ||
          intelligenceStatus === "failed" ||
          step === "complete" ||
          step === "failed" ||
          step === "ap_ready";
        return terminal ? false : 1500;
      },
      staleTime: 0,
      retry: false,
    })),
  });

  const items = useMemo(() => queries.map((q, i) => ({ id: ids[i], ...q.data, loading: q.isLoading, isError: q.isError })), [queries, ids]);

  // The old implementation persisted uploaded document IDs forever. That made
  // yesterday's documents reappear here as if they were still processing.
  // This list is now strictly a live-work list: terminal, not-requested and
  // missing documents are removed from local storage as soon as their state is
  // observed.
  useEffect(() => {
    if (typeof window === "undefined" || !items.length) return;

    const terminalIds = items
      .filter((item) => {
        if (item.isError) return true;
        const d: any = item.document;
        const intelligenceStatus = String(d?.intelligence_status || "not_requested").toLowerCase();
        const step = String(d?.processing_step || "").toLowerCase();
        return (
          intelligenceStatus === "not_requested" ||
          intelligenceStatus === "complete" ||
          intelligenceStatus === "failed" ||
          step === "complete" ||
          step === "failed" ||
          step === "ap_ready"
        );
      })
      .map((item) => item.id);

    if (!terminalIds.length) return;

    const terminalSet = new Set(terminalIds);
    const nextIds = ids.filter((id) => !terminalSet.has(id));
    localStorage.setItem(KEY, JSON.stringify(nextIds));
    setIds(nextIds);
  }, [items, ids]);

  if (!items.length) return null;

  return (
    <div className="card" style={{ marginBottom: 20, padding: 20 }}>
      <div className="section-card-header">
        <div>
          <div className="section-label">LIVE DOCUMENT WORK</div>
          <div className="section-card-name">Documents InvoiAI is processing</div>
        </div>
        <Link href="/dashboard/history" className="doc-action">My documents <ChevronRight size={13}/></Link>
      </div>
      <div style={{ display: "grid", gap: 10 }}>
        {items.map((item) => {
          const d: any = item.document;
          const failed = d?.processing_step === "failed" || d?.status === "failed";
          const ready = !!item.ready;
          return (
            <div key={item.id} className="active-upload-tracker-row">
              <Link href={`/dashboard/document/${item.id}`} style={{ display: "contents" }}>
                <div className="active-upload-icon">
                  {failed ? <XCircle size={17}/> : ready ? <CheckCircle2 size={17}/> : <Loader2 size={17} className="animate-spin"/>}
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div className="active-upload-name">{d?.file_name || "Document"}</div>
                  <div className="active-upload-message">{failed ? (d?.error_message || "Processing failed") : ready ? "Analysis complete — open the document to review results" : (d?.processing_message || "Document received — processing in the background")}</div>
                  {!ready && !failed && <div className="doc-progress-track" style={{ marginTop: 7 }}><div className="doc-progress-fill" style={{ width: `${Math.max(3, Math.min(100, d?.processing_progress || 0))}%` }}/></div>}
                </div>
                <span className="active-upload-percent">{ready ? "Ready" : failed ? "Failed" : `${d?.processing_progress || 0}%`}</span>
                <ChevronRight size={15}/>
              </Link>
              <button
                type="button"
                aria-label={`Dismiss ${d?.file_name || "document"} notification`}
                title="Dismiss notification"
                onClick={(event) => { event.preventDefault(); event.stopPropagation(); dismiss(item.id); }}
                style={{ background: "transparent", border: 0, cursor: "pointer", padding: 6, display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: 6 }}
              >
                <X size={15} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
