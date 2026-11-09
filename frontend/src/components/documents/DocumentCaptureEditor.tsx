"use client";

import { useMemo, useState } from "react";
import { Check, Loader2, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import toast from "react-hot-toast";
import { documentsApi } from "@/api/documents";
import { getErrorMessage } from "@/api/client";

type Option = { value: string; label: string; source: string; id?: string; code?: string };
type Line = Record<string, any>;

type Props = {
  documentId: string;
  documentData: Record<string, any>;
  lineItems: Line[];
  ocrFields: Record<string, any>;
  sourceUrl?: string;
  sourceMimeType?: string;
  documentType?: string;
  currency?: string;
  onSaved: () => Promise<void> | void;
  onCancel: () => void;
};

const coreFields = [
  ["vendor_name", "Vendor"], ["document_number", "Document number"], ["document_date", "Document date"],
  ["due_date", "Due date"], ["currency", "Currency"], ["payment_terms", "Payment terms"],
  ["payment_method", "Payment method"], ["subtotal", "Subtotal"], ["tax_rate", "Tax rate"],
  ["tax_amount", "Tax amount"], ["total_amount", "Total"], ["amount_due", "Amount due"],
  ["gl_account_name", "Account"], ["purchase_order_number", "Purchase order"],
] as const;

function labelize(value: string) { return value.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()); }

function inputValue(value: unknown): string { return value == null ? "" : String(value); }

export default function DocumentCaptureEditor({ documentId, documentData, lineItems, ocrFields, sourceUrl, sourceMimeType, documentType, currency, onSaved, onCancel }: Props) {
  const initialOverrides = (documentData.capture_overrides || {}) as Record<string, any>;
  const [values, setValues] = useState<Record<string, any>>(() => ({ ...documentData, ...initialOverrides }));
  const [lines, setLines] = useState<Line[]>(() => lineItems.map((item) => ({ ...item })));
  const [openField, setOpenField] = useState<string | null>(null);
  const [options, setOptions] = useState<Option[]>([]);
  const [optionQuery, setOptionQuery] = useState("");
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [saving, setSaving] = useState(false);

  const knownKeys = useMemo(() => new Set<string>(coreFields.map(([key]) => key)), []);
  const otherFields = Object.entries(ocrFields || {}).filter(([key, value]) => !knownKeys.has(key) && key !== "line_items" && key !== "reconciliation" && value != null && value !== "");

  const setValue = (field: string, value: any) => setValues((prev) => ({ ...prev, [field]: value }));

  // The OCR service and structured extractor may expose the same field under different names.
  // Offer every scalar captured value, not only the single server-side suggestion.
  const localCapturedOptions = (field: string, query = ""): Option[] => {
    const candidates: Option[] = [];
    const add = (key: string, value: unknown, source: string) => {
      if (value == null || typeof value === "object") return;
      const text = String(value).trim();
      if (!text) return;
      candidates.push({ value: text, label: `${labelize(key)}: ${text}`, source });
    };
    Object.entries(ocrFields || {}).forEach(([key, value]) => add(key, value, "ocr_capture"));
    Object.entries(documentData || {}).forEach(([key, value]) => add(key, value, "structured_capture"));
    Object.entries(values || {}).forEach(([key, value]) => add(key, value, "current_document"));
    lines.forEach((line, index) => Object.entries(line).forEach(([key, value]) => add(`line ${index + 1} ${key}`, value, "line_item")));
    const normalizedQuery = query.trim().toLowerCase();
    const unique = new Map<string, Option>();
    for (const option of candidates) {
      if (normalizedQuery && !`${option.value} ${option.label} ${option.source}`.toLowerCase().includes(normalizedQuery)) continue;
      const identity = `${option.value.toLowerCase()}|${option.source}`;
      if (!unique.has(identity)) unique.set(identity, option);
    }
    return [...unique.values()];
  };

  const mergeOptions = (remote: Option[], local: Option[]): Option[] => {
    const unique = new Map<string, Option>();
    for (const option of [...remote, ...local]) {
      const identity = `${String(option.value).toLowerCase()}|${option.id || option.source}`;
      if (!unique.has(identity)) unique.set(identity, option);
    }
    return [...unique.values()];
  };

  const openOptions = async (field: string) => {
    setOpenField(field);
    setOptionQuery("");
    setLoadingOptions(true);
    try {
      const response = await documentsApi.getCaptureOptions(documentId, field);
      setOptions(mergeOptions(response.options || [], localCapturedOptions(field)));
    } catch (error) {
      setOptions(localCapturedOptions(field));
      toast.error(getErrorMessage(error, "Could not load master-data suggestions. Showing values captured from this document."));
    } finally { setLoadingOptions(false); }
  };

  const searchOptions = async (field: string, query: string) => {
    setOptionQuery(query);
    setLoadingOptions(true);
    try {
      const response = await documentsApi.getCaptureOptions(documentId, field, query);
      setOptions(mergeOptions(response.options || [], localCapturedOptions(field, query)));
    } catch {
      setOptions(localCapturedOptions(field, query));
    }
    finally { setLoadingOptions(false); }
  };

  const openLineAccountOptions = async (index: number) => {
    const key = `line-account:${index}`;
    setOpenField(key);
    setOptionQuery("");
    setLoadingOptions(true);
    try {
      const response = await documentsApi.getCaptureOptions(documentId, "gl_account_name");
      setOptions(mergeOptions(response.options || [], localCapturedOptions("gl_account_name")));
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not load accounts."));
    } finally { setLoadingOptions(false); }
  };

  const chooseLineAccount = (index: number, option: Option) => {
    setLines((prev) => prev.map((line, i) => i === index ? { ...line, gl_account_id: option.id, gl_account_code: option.code, gl_account_name: option.value } : line));
    setOpenField(null);
  };

  const chooseOption = (field: string, option: Option) => {
    if (field === "vendor_name" && option.id) setValues((prev) => ({ ...prev, vendor_name: option.value, vendor_id: option.id }));
    else if (field === "gl_account_name") setValues((prev) => ({ ...prev, gl_account_name: option.value, gl_account_id: option.id, gl_account_code: option.code }));
    else if (field === "document_number" && option.source === "purchase_order") setValues((prev) => ({ ...prev, document_number: option.value, purchase_order_id: option.id, purchase_order_number: option.value }));
    else setValue(field, option.value);
    setOpenField(null);
  };

  const save = async () => {
    setSaving(true);
    try {
      const overrides: Record<string, any> = {};
      for (const [key] of otherFields) {
        if (values[key] !== undefined) overrides[key] = values[key];
      }
      if (values.purchase_order_number) overrides.purchase_order_number = values.purchase_order_number;
      await documentsApi.updateCapture(documentId, {
        document_type: values.document_type || documentType,
        vendor_id: values.vendor_id || undefined,
        vendor_name: values.vendor_name || null,
        document_number: values.document_number || null,
        document_date: values.document_date || null,
        due_date: values.due_date || null,
        currency: values.currency || null,
        payment_terms: values.payment_terms || null,
        payment_method: values.payment_method || null,
        subtotal: values.subtotal === "" ? null : values.subtotal,
        tax_rate: values.tax_rate === "" ? null : values.tax_rate,
        tax_amount: values.tax_amount === "" ? null : values.tax_amount,
        total_amount: values.total_amount === "" ? null : values.total_amount,
        amount_due: values.amount_due === "" ? null : values.amount_due,
        gl_account_id: values.gl_account_id || undefined,
        gl_account_code: values.gl_account_code || undefined,
        gl_account_name: values.gl_account_name || undefined,
        purchase_order_id: values.purchase_order_id || undefined,
        overrides,
        lines: lines.map((line) => ({
          description: line.description || "", quantity: line.quantity || 0, unit_price: line.unit_price || 0, amount: line.amount || 0,
          sku: line.sku || null, product_code: line.product_code || null, tax_rate: line.tax_rate ?? null, tax_amount: line.tax_amount ?? null,
          gl_account_id: line.gl_account_id || null, gl_account_code: line.gl_account_code || null, gl_account_name: line.gl_account_name || null,
        })),
      });
      toast.success("Document corrections saved.");
      await onSaved();
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not save document corrections."));
    } finally { setSaving(false); }
  };

  const updateLine = (index: number, field: string, value: any) => setLines((prev) => prev.map((line, i) => i === index ? { ...line, [field]: value } : line));
  const addLine = () => setLines((prev) => [...prev, { description: "", quantity: 1, unit_price: 0, amount: 0 }]);
  const removeLine = (index: number) => setLines((prev) => prev.filter((_, i) => i !== index));

  const isPdf = /pdf/i.test(sourceMimeType || "");

  return (
    <div className="card" style={{ marginBottom: 18, padding: 14, border: "1px solid #DCCFAE" }}>
      <div className="section-card-header" style={{ marginBottom: 12 }}>
        <div><div className="section-card-name">Edit captured data</div><div className="muted" style={{ marginTop: 3, fontSize: 11 }}>Correct any field, choose another captured value, search your master data, or enter a value manually. Original OCR remains preserved.</div></div>
        <button className="doc-action" onClick={onCancel}><X size={14}/> Close edit mode</button>
      </div>

      <div className="capture-editor">
        <div className="capture-editor-panel">
          <div className="capture-editor-head"><strong>Original document</strong><span className="badge">Source preserved</span></div>
          {sourceUrl ? (isPdf ? <iframe src={sourceUrl} title="Original document" style={{ width: "100%", height: 760, border: 0 }} /> : <img src={sourceUrl} alt="Original document" style={{ display: "block", width: "100%", maxHeight: 760, objectFit: "contain", background: "#F7F5F0" }} />) : <div style={{ padding: 30 }} className="muted">Source preview unavailable.</div>}
        </div>

        <div className="capture-editor-panel">
          <div className="capture-editor-head"><strong>Captured fields</strong><span className="badge">Editable</span></div>
          <div className="capture-editor-body">
            <div className="capture-field" style={{ marginBottom: 14 }}>
              <div className="capture-field-label"><span>Document type</span><span>Human correction</span></div>
              <select className="capture-field-input" value={inputValue(values.document_type || documentType || "unknown")} onChange={(e) => setValue("document_type", e.target.value)}>
                {["invoice","receipt","purchase_order","credit_note","debit_note","delivery_note","quotation","contract","bank_statement","expense_report","tax_document","financial_statement","unknown"].map((type) => <option key={type} value={type}>{labelize(type)}</option>)}
              </select>
            </div>
            <div className="capture-field-grid">
              {coreFields.map(([field, label]) => {
                const value = inputValue(values[field]);
                const isAccount = field === "gl_account_name";
                const isVendor = field === "vendor_name";
                return <div className={`capture-field${field === "purchase_order_number" ? " full" : ""}`} key={field}>
                  <div className="capture-field-label"><span>{label}</span><span className="capture-field-tools"><button type="button" className="capture-icon-btn" title="Choose captured/master value" onClick={() => void openOptions(field)}><Search size={12}/></button></span></div>
                  <input className="capture-field-input" value={value} onChange={(e) => setValue(field, e.target.value)} />
                  {openField === field && <div className="capture-options">
                    <input autoFocus className="capture-field-input" placeholder={isAccount ? "Search chart of accounts…" : isVendor ? "Search vendors…" : "Search captured values…"} value={optionQuery} onChange={(e) => void searchOptions(field, e.target.value)} />
                    {loadingOptions ? <div className="muted" style={{ padding: 10 }}><Loader2 size={13} className="animate-spin"/> Searching…</div> : options.length === 0 ? <div className="muted" style={{ padding: 10, fontSize: 11 }}>No matching values. You can type the correct value manually.</div> : options.map((option, index) => <button type="button" className="capture-option" key={`${option.value}-${index}`} onClick={() => chooseOption(field, option)}>{option.label}<span className="capture-option-meta">{option.source.replace(/_/g, " ")}</span></button>)}
                  </div>}
                </div>;
              })}
            </div>

            {otherFields.length > 0 && <div style={{ marginTop: 18 }}><div className="section-card-name" style={{ marginBottom: 9 }}>Other captured fields</div><div className="capture-field-grid">{otherFields.map(([key, value]) => <div className="capture-field" key={key}><div className="capture-field-label"><span>{labelize(key)}</span><span className="capture-field-tools"><Pencil size={11}/></span></div><input className="capture-field-input" value={inputValue(values[key] ?? value)} onChange={(e) => setValue(key, e.target.value)}/></div>)}</div></div>}

            <div style={{ marginTop: 18 }}>
              <div className="section-card-header" style={{ padding: 0, border: 0, marginBottom: 9 }}><div className="section-card-name">Line items</div><button type="button" className="doc-action" onClick={addLine}><Plus size={13}/> Add line</button></div>
              <div className="capture-lines"><table className="section-table"><thead><tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th><th>Account</th><th></th></tr></thead><tbody>{lines.map((line, index) => <tr key={index}><td><input value={inputValue(line.description)} onChange={(e) => updateLine(index, "description", e.target.value)}/></td><td><input value={inputValue(line.quantity)} onChange={(e) => updateLine(index, "quantity", e.target.value)}/></td><td><input value={inputValue(line.unit_price)} onChange={(e) => updateLine(index, "unit_price", e.target.value)}/></td><td><input value={inputValue(line.amount)} onChange={(e) => updateLine(index, "amount", e.target.value)}/></td><td style={{ position: "relative" }}><div style={{ display: "flex", gap: 4 }}><input value={inputValue(line.gl_account_name)} placeholder="Account" onChange={(e) => updateLine(index, "gl_account_name", e.target.value)}/><button type="button" className="capture-icon-btn" title="Search account" onClick={() => void openLineAccountOptions(index)}><Search size={11}/></button></div>{openField === `line-account:${index}` && <div className="capture-options" style={{ position: "absolute", right: 0, top: "100%", width: 280 }}>{loadingOptions ? <div className="muted" style={{ padding: 10 }}>Searching…</div> : options.map((option, optionIndex) => <button type="button" className="capture-option" key={`${option.value}-${optionIndex}`} onClick={() => chooseLineAccount(index, option)}>{option.label}<span className="capture-option-meta">{option.source.replace(/_/g, " ")}</span></button>)}</div>}</td><td><button type="button" className="capture-icon-btn" title="Remove line" onClick={() => removeLine(index)}><Trash2 size={12}/></button></td></tr>)}</tbody></table></div>
            </div>

            <div className="capture-savebar"><button className="doc-action" onClick={onCancel} disabled={saving}><X size={14}/> Cancel</button><button className="doc-action primary" onClick={() => void save()} disabled={saving}>{saving ? <Loader2 size={14} className="animate-spin"/> : <Check size={14}/>} {saving ? "Saving…" : "Save corrections"}</button></div>
          </div>
        </div>
      </div>
    </div>
  );
}
