"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Save, Sparkles, X } from "lucide-react";
import toast from "react-hot-toast";
import { apApi, ChartOfAccount, InvoiceCoding } from "@/api/ap";
import { getErrorMessage } from "@/api/client";

interface Props {
  invoiceId: string;
  apStatus: string;
  glCodingStatus: string | null;
  lineItems: Array<{
    id: string;
    description?: string | null;
    quantity?: number | null;
    unit_price?: number | null;
    amount?: number | null;
    gl_account_id?: string | null;
    gl_account_code?: string | null;
    gl_account_name?: string | null;
  }>;
  onCodingSaved: () => void;
}

export default function GLCodingPanel({
  invoiceId,
  apStatus,
  glCodingStatus,
  lineItems,
  onCodingSaved,
}: Props) {
  const [accounts, setAccounts] = useState<ChartOfAccount[]>([]);
  const [codings, setCodings] = useState<Record<string, InvoiceCoding>>({});
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [accts, existingCodings] = await Promise.all([
          apApi.listChartOfAccounts(true),
          apApi.getCodings(invoiceId),
        ]);
        setAccounts(accts);
        const codingMap: Record<string, InvoiceCoding> = {};
        for (const c of existingCodings) {
          if (c.line_item_id) codingMap[c.line_item_id] = c;
        }
        setCodings(codingMap);
      } catch (err) {
        toast.error(getErrorMessage(err, "Could not load accounts or codings."));
      } finally {
        setLoadingAccounts(false);
      }
    }
    if (apStatus === "coding" || apStatus === "coding_exception") {
      load();
    }
  }, [invoiceId, apStatus]);

  const postableAccounts = useMemo(() => {
    return accounts.filter((a) => a.is_postable && (showInactive || a.is_active));
  }, [accounts, showInactive]);

  const accountOptions = useMemo(() => {
    return postableAccounts.map((a) => ({
      value: a.id,
      label: `${a.account_code} — ${a.account_name}`,
      code: a.account_code,
      name: a.account_name,
    }));
  }, [postableAccounts]);

  const handleSave = async (lineItemId: string, glAccountId: string, amount?: number) => {
    if (saving === lineItemId) return;
    setSaving(lineItemId);
    try {
      const account = postableAccounts.find((a) => a.id === glAccountId);
      if (!account) throw new Error("Account not found");

      await apApi.saveLineCoding(invoiceId, lineItemId, {
        gl_account_id: glAccountId,
        amount,
      });

      setCodings((prev) => ({
        ...prev,
        [lineItemId]: {
          id: "",
          document_id: invoiceId,
          line_item_id: lineItemId,
          gl_account_id: glAccountId,
          account_code: account.account_code,
          account_name: account.account_name,
          confidence: 100,
          status: "approved",
          source: "manual",
        },
      }));

      toast.success(`Saved ${account.account_code} — ${account.account_name}`);
      onCodingSaved();
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not save coding."));
    } finally {
      setSaving(null);
    }
  };

  const handleCreateRule = async (lineItemId: string, glAccountId: string, description: string) => {
    const account = postableAccounts.find((a) => a.id === glAccountId);
    if (!account) return;
    try {
      await apApi.createCodingRule({
        name: `Auto-code: ${description.slice(0, 40)}`,
        description: `Auto-assign ${account.account_code} ${account.account_name} for similar lines`,
        description_pattern: description,
        gl_account_id: glAccountId,
        priority: 100,
      });
      toast.success("Coding rule created — future similar lines will be auto-coded");
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not create rule."));
    }
  };

  if (loadingAccounts) {
    return (
      <section className="panel" style={{ padding: 22, borderRadius: 18 }}>
        <div className="section-card-name" style={{ marginBottom: 18 }}>Assign GL accounts</div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, color: "#6B6860" }}>
          <Loader2 className="spin" size={18} /> Loading accounts and saved codings…
        </div>
      </section>
    );
  }

  const isCodingPhase = apStatus === "coding" || apStatus === "coding_exception";
  const allLinesCoded = lineItems.every(
    (line) => codings[line.id]?.gl_account_id || line.gl_account_id
  );

  if (!isCodingPhase) return null;

  return (
    <section className="panel" style={{ padding: 22, borderRadius: 18 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap", marginBottom: 18 }}>
        <div>
          <div className="section-card-name">Assign GL accounts</div>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#6B6860" }}>
            Each line needs a postable account. Manual saves survive re-coding.{" "}
            {accountOptions.length === 0 && <span style={{ color: "#C0392B" }}> No postable accounts — add them in Settings → Accounting first.</span>}
          </p>
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12.5, color: "#6B6860" }}>
          <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
          Show inactive
        </label>
      </div>

      {lineItems.length === 0 && (
        <div className="soft-notice">No line items found on this invoice.</div>
      )}

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", minWidth: 720, borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "#8B857C", fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".08em" }}>
              <th style={{ padding: "8px 10px", width: 60 }}>#</th>
              <th style={{ padding: "8px 10px" }}>Description</th>
              <th style={{ padding: "8px 10px", width: 100 }}>Amount</th>
              <th style={{ padding: "8px 10px", width: 280 }}>GL Account</th>
              <th style={{ padding: "8px 10px", width: 120, textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {lineItems.map((line, idx) => {
              const coding = codings[line.id];
              const hasAccount = coding?.gl_account_id || line.gl_account_id;
              const accountCode = coding?.account_code || line.gl_account_code;
              const accountName = coding?.account_name || line.gl_account_name;
              const confidence = coding?.confidence;
              const source = coding?.source || (line.gl_account_id ? "manual" : "none");

              return (
                <tr key={line.id} style={{ borderTop: "1px solid #EBE6DC" }}>
                  <td style={{ padding: "11px 10px", fontVariantNumeric: "tabular-nums", fontWeight: 750 }}>{idx + 1}</td>
                  <td style={{ padding: "11px 10px" }}>
                    <div style={{ fontWeight: 500 }}>{line.description || "—"}</div>
                    <div style={{ fontSize: 11, color: "#6B6860" }}>
                      Qty: {line.quantity ?? "—"} × Unit: {line.unit_price ? `$${Number(line.unit_price).toFixed(2)}` : "—"}
                    </div>
                  </td>
                  <td style={{ padding: "11px 10px", fontVariantNumeric: "tabular-nums" }}>
                    {line.amount ? `$${Number(line.amount).toFixed(2)}` : "—"}
                  </td>
                  <td style={{ padding: "11px 10px" }}>
                    {hasAccount ? (
                      <div>
                        <div style={{ fontWeight: 600 }}>{accountCode}</div>
                        <div style={{ fontSize: 12, color: "#6B6860" }}>{accountName}</div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6, fontSize: 11 }}>
                          <span className={`badge ${source === "manual" ? "badge-done" : source === "ai_suggested" ? "badge-info" : "badge-muted"}`}>
                            {source === "manual" ? "Manual" : source === "ai_suggested" ? "AI" : source === "rule" ? "Rule" : source === "historical" ? "History" : source}
                          </span>
                          {confidence != null && (
                            <span style={{ color: confidence >= 80 ? "#477453" : confidence >= 60 ? "#B7791F" : "#C0392B" }}>
                              {confidence}% confidence
                            </span>
                          )}
                        </div>
                      </div>
                    ) : (
                      <select
                        className="settings-control"
                        style={{ width: "100%", maxWidth: 260 }}
                        value=""
                        onChange={(e) => e.target.value && handleSave(line.id, e.target.value, line.amount ?? undefined)}
                        disabled={saving === line.id || accountOptions.length === 0}
                        aria-label={`Select GL account for ${line.description || "line"}`}
                      >
                        <option value="" disabled selected>
                          — Select account —
                        </option>
                        {accountOptions.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td style={{ padding: "11px 10px", textAlign: "right", whiteSpace: "nowrap" }}>
                    {hasAccount && (
                      <>
                        <button
                          type="button"
                          className="btn-quiet"
                          style={{ minHeight: 0, padding: "6px 8px", marginRight: 6 }}
                          onClick={() => handleCreateRule(line.id, coding!.gl_account_id!, line.description || "")}
                          title="Save as coding rule for future similar lines"
                        >
                          <Sparkles size={14} /> Rule
                        </button>
                        <button
                          type="button"
                          className="btn-quiet"
                          style={{ minHeight: 0, padding: "6px 8px" }}
                          onClick={() => {
                            const newCodings = { ...codings };
                            delete newCodings[line.id];
                            setCodings(newCodings);
                            handleSave(line.id, "", line.amount ?? undefined);
                          }}
                          title="Clear this assignment"
                        >
                          <X size={14} /> Clear
                        </button>
                      </>
                    )}
                    {saving === line.id && <Loader2 className="spin" size={16} style={{ color: "#3F6B4A" }} />}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {lineItems.length > 0 && (
        <div style={{ marginTop: 16, padding: 16, background: "#F8FCF8", border: "1px solid #D6E6D8", borderRadius: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <div style={{ fontSize: 13, color: allLinesCoded ? "#477453" : "#B7791F" }}>
              <strong>{allLinesCoded ? "All lines coded" : `${lineItems.filter((l) => codings[l.id]?.gl_account_id || l.gl_account_id).length} of ${lineItems.length} lines coded`}</strong>
            </div>
            {allLinesCoded && (
              <span className="badge badge-done" style={{ fontSize: 12 }}>Ready to submit for approval</span>
            )}
          </div>
        </div>
      )}
    </section>
  );
}