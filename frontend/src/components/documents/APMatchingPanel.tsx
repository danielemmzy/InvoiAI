"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, ChevronDown, FileUp, Loader2, X } from "lucide-react";
import toast from "react-hot-toast";
import { apApi, APMatchMode, APStatus } from "@/api/ap";
import { documentsApi } from "@/api/documents";
import { useRouter } from "next/navigation";

interface Props {
  invoiceId: string;
  vendorId?: string | null;
  initialStatus?: APStatus | null;
  onClose: () => void;
  onSaved?: (status: APStatus) => void;
}

type PO = { id: string; po_number?: string; vendor_id?: string | null; vendor_name?: string | null; amount?: number; currency?: string; is_open?: boolean };
type Receipt = { id: string; receipt_number?: string | null; purchase_order_id?: string; status?: string; received_at?: string; goods_receipt_lines?: Array<{ description?: string; quantity_received?: number }> };

const MODES: Array<{ value: APMatchMode; label: string; help: string }> = [
  { value: "non_po", label: "Non-PO", help: "Invoice is processed without a purchase order or receipt." },
  { value: "two_way", label: "2-way", help: "Invoice is matched against a selected purchase order." },
  { value: "three_way", label: "3-way", help: "Invoice is matched against a selected purchase order and goods receipt." },
];



export default function APMatchingPanel({ invoiceId, vendorId, initialStatus, onClose, onSaved }: Props) {
  const [mode, setMode] = useState<APMatchMode>((initialStatus?.ap_match_mode as APMatchMode) || "two_way");
  const [poId, setPoId] = useState(initialStatus?.purchase_order_id || "");
  const [receiptId, setReceiptId] = useState(initialStatus?.goods_receipt_id || "");
  const [pos, setPos] = useState<PO[]>([]);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState<"purchase_order" | "goods_receipt" | null>(null);
  const selectRequested = useRef(false);
  const runInFlight = useRef(false);
  const selectedPO = useMemo(() => pos.find((p) => p.id === poId), [pos, poId]);
  const router = useRouter();

  const loadPOs = async () => {
    try {
      const data = await apApi.listMatchingPurchaseOrders(vendorId || undefined);
      setPos(Array.isArray(data) ? data : []);
    } catch (e) {
      toast.error("Could not load purchase orders.");
    }
  };

  const loadReceipts = async (id: string) => {
    if (!id) { setReceipts([]); return; }
    try {
      const data = await apApi.listMatchingReceipts(id);
      setReceipts(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Could not load goods receipts.");
      setReceipts([]);
    }
  };

  useEffect(() => {
    if (!selectRequested.current) {
      selectRequested.current = true;
      void apApi.selectInvoice(invoiceId).catch(() => { selectRequested.current = false; });
    }
    void loadPOs();
  }, [invoiceId, vendorId]);
  useEffect(() => { void loadReceipts(poId); }, [poId]);

  const convertUploaded = async (file: File, type: "purchase_order" | "goods_receipt") => {
    setUploading(type);
    try {
      if (type === "goods_receipt" && !poId) {
        toast.error("Select the purchase order first, then upload the goods receipt.");
        return;
      }
      const uploaded = await apApi.uploadReferenceDocument(file, type);
      for (let i = 0; i < 30; i += 1) {
        const doc = await documentsApi.getById(uploaded.document_id);
        if (["failed", "rejected"].includes(String(doc.status))) throw new Error("Reference document processing failed.");
        if (doc.status && !["ocr_running", "processing", "queued", "received"].includes(String(doc.status))) break;
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      const converted = await apApi.convertReferenceDocument(uploaded.document_id, type === "goods_receipt" ? poId : undefined);
      if (!converted?.ready) throw new Error("Reference document is still processing. Try again shortly.");
      if (type === "purchase_order") {
        setPoId(String(converted.purchase_order_id));
        await loadPOs();
        toast.success("Purchase order uploaded and added to the selectable list.");
      } else {
        setReceiptId(String(converted.goods_receipt_id));
        await loadReceipts(poId);
        toast.success("Goods receipt uploaded and added to the selected purchase order.");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not upload the reference document.");
    } finally {
      setUploading(null);
    }
  };

  const run = async () => {
    if (runInFlight.current) return;
    if (mode === "two_way" && !poId) { toast.error("Select or upload a purchase order for 2-way matching."); return; }
    if (mode === "three_way" && (!poId || !receiptId)) { toast.error("Select/upload both a purchase order and a goods receipt for 3-way matching."); return; }
    runInFlight.current = true;
    setLoading(true);
    try {
      if (typeof window !== "undefined") {
        const key = "invoiai-active-document-ids";
        try {
          const existing = JSON.parse(localStorage.getItem(key) || "[]");
          localStorage.setItem(key, JSON.stringify(Array.from(new Set([...existing, invoiceId])).slice(-20)));
        } catch {
          localStorage.setItem(key, JSON.stringify([invoiceId]));
        }
      }
      const result = await apApi.run(invoiceId, {
        match_mode: mode,
        purchase_order_id: mode === "non_po" ? null : poId,
        goods_receipt_id: mode === "three_way" ? receiptId : null,
      });
      // The run endpoint has already persisted the match context and queued processing.
      // Do not block navigation on a second status request: a transient status timeout
      // must not make a successful start look like a failed submission.
      const status: APStatus = {
        id: invoiceId,
        ap_enabled: true,
        ap_status: result?.ap_status || "validating",
        ap_match_mode: mode,
        purchase_order_id: mode === "non_po" ? null : poId,
        goods_receipt_id: mode === "three_way" ? receiptId : null,
        processing_step: "ap_preparing",
        processing_message: "Preparing invoice data for Accounts Payable…",
        processing_progress: 10,
      };
      onSaved?.(status);
      toast.success(mode === "three_way" ? "3-way matching started." : mode === "two_way" ? "2-way matching started." : "Non-PO AP processing started.");
      router.push(`/dashboard/document/${invoiceId}/ap-processing`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not start AP matching.");
    } finally {
      runInFlight.current = false;
      setLoading(false);
    }
  };

  return (
    <div id="ap-matching-panel" className="card" style={{ marginBottom: 16, padding: 20, border: "1px solid #DCCFAE", scrollMarginTop: 18 }}>
      <div className="section-card-header">
        <div>
          <div className="section-card-name">AP matching</div>
          <div style={{ fontSize: 12, color: "#6B6860", marginTop: 4 }}>Selected invoice: <strong>{invoiceId.slice(0, 8)}</strong></div>
        </div>
        <button className="drawer-close" type="button" onClick={onClose} aria-label="Close AP matching"><X size={18} /></button>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "14px 0" }}>
        {MODES.map((item) => (
          <button key={item.value} type="button" className={`doc-action ${mode === item.value ? "primary" : ""}`} onClick={() => { setMode(item.value); if (item.value === "non_po") { setPoId(""); setReceiptId(""); } }}>
            {item.label}
          </button>
        ))}
      </div>
      <div className="soft-notice" style={{ marginBottom: 14 }}>{MODES.find((m) => m.value === mode)?.help}</div>

      {mode !== "non_po" && (
        <div style={{ display: "grid", gap: 12 }}>
          <label className="kv-row" style={{ display: "grid", gap: 6 }}>
            <span className="kv-key">Purchase order</span>
            <select className="ap-filter-select" value={poId} onChange={(e) => { setPoId(e.target.value); setReceiptId(""); }}>
              <option value="">Select a purchase order…</option>
              {pos.map((po) => <option key={po.id} value={po.id}>{po.po_number || po.id.slice(0, 8)} · {po.amount ?? "—"} {po.currency || ""}</option>)}
            </select>
          </label>
          {selectedPO && <div className="soft-notice">Selected PO: <strong>{selectedPO.po_number || selectedPO.id}</strong> · {selectedPO.amount ?? "—"} {selectedPO.currency || ""}</div>}
          <label className="doc-action" style={{ width: "fit-content", cursor: uploading === "purchase_order" ? "wait" : "pointer" }}>
            <FileUp size={14} /> {uploading === "purchase_order" ? "Uploading PO…" : "Upload purchase order"}
            <input type="file" hidden accept="application/pdf,image/*" disabled={!!uploading} onChange={(e) => { const file = e.target.files?.[0]; if (file) void convertUploaded(file, "purchase_order"); e.currentTarget.value = ""; }} />
          </label>
        </div>
      )}

      {mode === "three_way" && poId && (
        <div style={{ display: "grid", gap: 12, marginTop: 14 }}>
          <label className="kv-row" style={{ display: "grid", gap: 6 }}>
            <span className="kv-key">Goods receipt</span>
            <select className="ap-filter-select" value={receiptId} onChange={(e) => setReceiptId(e.target.value)}>
              <option value="">Select a confirmed receipt…</option>
              {receipts.map((receipt) => <option key={receipt.id} value={receipt.id}>{receipt.receipt_number || receipt.id.slice(0, 8)} · {receipt.status || ""}</option>)}
            </select>
          </label>
          <label className="doc-action" style={{ width: "fit-content", cursor: uploading === "goods_receipt" ? "wait" : "pointer" }}>
            <FileUp size={14} /> {uploading === "goods_receipt" ? "Uploading receipt…" : "Upload goods receipt"}
            <input type="file" hidden accept="application/pdf,image/*" disabled={!!uploading} onChange={(e) => { const file = e.target.files?.[0]; if (file) void convertUploaded(file, "goods_receipt"); e.currentTarget.value = ""; }} />
          </label>
          {!receipts.length && <div className="soft-notice">No confirmed receipt is linked to this purchase order yet. Select or upload one.</div>}
        </div>
      )}

      <div className="doc-actions" style={{ marginTop: 18 }}>
        <button className="doc-action" type="button" onClick={onClose} disabled={loading || !!uploading}><X size={14} /> Close</button>
        <button className="doc-action primary" type="button" onClick={() => void run()} disabled={loading || !!uploading}>
          {loading ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
          {loading ? "Saving…" : mode === "three_way" ? "Start 3-way match" : mode === "two_way" ? "Start 2-way match" : "Start non-PO AP"}
        </button>
      </div>
    </div>
  );
}
