"use client";
// Accounting settings — /dashboard/settings/accounting
// The chart of accounts is the list of accounts AP coding is allowed to use.
// InvoiAI never invents an account, so this page is the setup surface that
// makes invoice coding possible for a new organization.

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Loader2, Pencil, Plus, Power, Search, Sparkles, X } from "lucide-react";
import toast from "react-hot-toast";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { EmptyState, PageError, PageLoading } from "@/components/ui/PageState";
import { apApi, ChartOfAccount } from "@/api/ap";
import { getErrorMessage } from "@/api/client";
import { useAppStore } from "@/store/useAppStore";

const ACCOUNT_TYPES = ["expense", "asset", "liability", "equity", "revenue"] as const;

type Draft = {
  id?: string;
  account_code: string;
  account_name: string;
  account_type: (typeof ACCOUNT_TYPES)[number];
  account_subtype: string;
  is_postable: boolean;
  is_active: boolean;
};

const emptyDraft: Draft = {
  account_code: "",
  account_name: "",
  account_type: "expense",
  account_subtype: "",
  is_postable: true,
  is_active: true,
};

export default function ChartOfAccountsPage() {
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  const qc = useQueryClient();
  const { data, isPending, isError, error: queryError } = useQuery({
    queryKey: ["chart-of-accounts", "all", ws],
    queryFn: () => apApi.listChartOfAccounts(true),
    staleTime: 60_000,
  });
  const accounts: ChartOfAccount[] = useMemo(() => data ?? [], [data]);
  const loading = isPending;
  const error = isError
    ? getErrorMessage(queryError, "Could not load the chart of accounts.")
    : null;

  const [search, setSearch] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saving, setSaving] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    await qc.invalidateQueries({ queryKey: ["chart-of-accounts"] });
  }

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return accounts.filter((account) => {
      if (!showInactive && !account.is_active) return false;
      if (!needle) return true;
      return `${account.account_code} ${account.account_name} ${account.account_type}`.toLowerCase().includes(needle);
    });
  }, [accounts, search, showInactive]);

  const activeCount = accounts.filter((account) => account.is_active).length;
  const postableCount = accounts.filter((account) => account.is_active && account.is_postable).length;

  async function seed() {
    setSeeding(true);
    try {
      const result = await apApi.seedChartOfAccounts();
      toast.success(
        result.created
          ? `Added ${result.created} starter account${result.created === 1 ? "" : "s"}.`
          : "Starter accounts are already present.",
      );
      await load();
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not load the starter chart of accounts."));
    } finally {
      setSeeding(false);
    }
  }

  async function save() {
    if (!draft) return;
    if (!draft.account_code.trim() || !draft.account_name.trim()) {
      toast.error("Account code and name are required.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        account_code: draft.account_code.trim(),
        account_name: draft.account_name.trim(),
        account_type: draft.account_type,
        account_subtype: draft.account_subtype.trim() || null,
        is_postable: draft.is_postable,
        is_active: draft.is_active,
      };
      if (draft.id) await apApi.updateChartOfAccount(draft.id, payload);
      else await apApi.createChartOfAccount(payload);
      toast.success(draft.id ? "Account updated." : "Account added.");
      setDraft(null);
      await load();
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not save this account."));
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(account: ChartOfAccount) {
    setBusyId(account.id);
    try {
      if (account.is_active) await apApi.deactivateChartOfAccount(account.id);
      else await apApi.updateChartOfAccount(account.id, { is_active: true });
      toast.success(account.is_active ? "Account deactivated." : "Account reactivated.");
      await load();
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not update this account."));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <DashboardLayout>
      <div className="page-head">
        <div>
          <div className="eyebrow">Settings · Accounting</div>
          <h1 className="page-title">Chart of accounts</h1>
          <p className="page-subtitle">
            These are the accounts every invoice line can be coded to. InvoiAI never invents an account:
            if the right account is missing here, the line waits for review.
          </p>
        </div>
      </div>

      <div className="soft-notice" style={{ marginBottom: 18 }}>
        <BookOpen size={17} style={{ flex: "0 0 auto", marginTop: 1 }} />
        <div>
          <strong>Start with the starter chart</strong>, then rename, add, or deactivate accounts to match your books.
          Connecting QuickBooks replaces the starter list with your real chart.
        </div>
      </div>

      {draft && (
        <section className="panel" style={{ padding: 22 }}>
          <div className="panel-head" style={{ marginBottom: 14 }}>
            <div>
              <div className="panel-kicker">{draft.id ? "Edit account" : "New account"}</div>
              <h2>{draft.id ? "Update account details" : "Add an account"}</h2>
            </div>
            <button type="button" className="btn-quiet" onClick={() => setDraft(null)} aria-label="Close form">
              <X size={16} />
            </button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14 }}>
            <label style={{ display: "grid", gap: 6, fontSize: 12, fontWeight: 650 }}>
              Code
              <input className="settings-control" value={draft.account_code} onChange={(e) => setDraft({ ...draft, account_code: e.target.value })} placeholder="6100" />
            </label>
            <label style={{ display: "grid", gap: 6, fontSize: 12, fontWeight: 650 }}>
              Name
              <input className="settings-control" value={draft.account_name} onChange={(e) => setDraft({ ...draft, account_name: e.target.value })} placeholder="Software &amp; Subscriptions" />
            </label>
            <label style={{ display: "grid", gap: 6, fontSize: 12, fontWeight: 650 }}>
              Type
              <select className="settings-control" value={draft.account_type} onChange={(e) => setDraft({ ...draft, account_type: e.target.value as Draft["account_type"] })}>
                {ACCOUNT_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
            </label>
            <label style={{ display: "grid", gap: 6, fontSize: 12, fontWeight: 650 }}>
              Subtype (optional)
              <input className="settings-control" value={draft.account_subtype} onChange={(e) => setDraft({ ...draft, account_subtype: e.target.value })} placeholder="operating_expense" />
            </label>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap", marginTop: 16 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
              <input type="checkbox" checked={draft.is_postable} onChange={(e) => setDraft({ ...draft, is_postable: e.target.checked })} />
              Postable (invoice lines may use it)
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
              <input type="checkbox" checked={draft.is_active} onChange={(e) => setDraft({ ...draft, is_active: e.target.checked })} />
              Active
            </label>
            <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
              <button type="button" className="btn-secondary" onClick={() => setDraft(null)}>Cancel</button>
              <button type="button" className="doc-action primary" onClick={() => void save()} disabled={saving}>
                {saving ? <Loader2 className="spin" size={15} /> : <Plus size={15} />}
                {saving ? "Saving…" : draft.id ? "Save changes" : "Add account"}
              </button>
            </div>
          </div>
        </section>
      )}

      {loading ? (
        <PageLoading variant="table" rows={6} />
      ) : error ? (
        <PageError message={error} onRetry={() => void load()} />
      ) : accounts.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No chart of accounts yet"
          message="AP coding cannot assign an account until the chart exists. Load a standard starter chart, then adjust it to match your books."
          action={
            <button type="button" className="doc-action primary" onClick={() => void seed()} disabled={seeding}>
              {seeding ? <Loader2 className="spin" size={15} /> : <Sparkles size={15} />}
              {seeding ? "Loading starter chart…" : "Load starter chart of accounts"}
            </button>
          }
        />
      ) : (
        <section className="panel" style={{ padding: 22 }}>
          {postableCount === 0 && (
            <div className="warning-box" style={{ marginBottom: 16 }}>
              <strong>No active, postable account.</strong> AP coding has nowhere to assign an invoice line, so every
              line will wait for review. Reactivate an account or add one before coding invoices.
            </div>
          )}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", marginBottom: 16 }}>
            <div style={{ position: "relative", flex: "1 1 240px", maxWidth: 340 }}>
              <Search size={15} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#8B857C" }} />
              <input
                className="settings-control"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search code or name"
                aria-label="Search chart of accounts"
                style={{ paddingLeft: 34, width: "100%" }}
              />
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12.5, color: "#6B6860" }}>
              <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
              Show inactive
            </label>
            <span style={{ marginLeft: "auto", fontSize: 12.5, color: "#6B6860" }}>
              {activeCount} active · {postableCount} postable
            </span>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => void seed()}
              disabled={seeding}
              style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
            >
              {seeding ? <Loader2 className="spin" size={14} /> : <Sparkles size={14} />}
              {seeding ? "Loading…" : "Load starter accounts"}
            </button>
            <button type="button" className="doc-action primary" onClick={() => setDraft({ ...emptyDraft })}>
              <Plus size={15} /> Add account
            </button>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", minWidth: 640, borderCollapse: "collapse", fontSize: 13 }}>
              <caption className="sr-only">Chart of accounts</caption>
              <thead>
                <tr style={{ textAlign: "left", color: "#8B857C", fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".08em" }}>
                  <th style={{ padding: "8px 10px", width: 90 }}>Code</th>
                  <th style={{ padding: "8px 10px" }}>Name</th>
                  <th style={{ padding: "8px 10px", width: 110 }}>Type</th>
                  <th style={{ padding: "8px 10px", width: 100 }}>Status</th>
                  <th style={{ padding: "8px 10px", width: 150, textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((account) => (
                  <tr key={account.id} style={{ borderTop: "1px solid #EBE6DC", opacity: account.is_active ? 1 : 0.55 }}>
                    <td style={{ padding: "11px 10px", fontVariantNumeric: "tabular-nums", fontWeight: 750 }}>{account.account_code}</td>
                    <td style={{ padding: "11px 10px" }}>
                      {account.account_name}
                      {!account.is_postable && <span className="badge badge-muted" style={{ marginLeft: 8 }}>header only</span>}
                    </td>
                    <td style={{ padding: "11px 10px", textTransform: "capitalize", color: "#6B6860" }}>{account.account_type}</td>
                    <td style={{ padding: "11px 10px" }}>
                      <span className={`badge ${account.is_active ? "badge-done" : "badge-muted"}`}>{account.is_active ? "active" : "inactive"}</span>
                    </td>
                    <td style={{ padding: "11px 10px", textAlign: "right", whiteSpace: "nowrap" }}>
                      <button
                        type="button"
                        className="btn-quiet"
                        style={{ minHeight: 0, padding: "6px 8px" }}
                        onClick={() => setDraft({
                          id: account.id,
                          account_code: account.account_code,
                          account_name: account.account_name,
                          account_type: (ACCOUNT_TYPES as readonly string[]).includes(account.account_type ?? "") ? (account.account_type as Draft["account_type"]) : "expense",
                          account_subtype: account.account_subtype || "",
                          is_postable: account.is_postable,
                          is_active: account.is_active,
                        })}
                        aria-label={`Edit ${account.account_name}`}
                      >
                        <Pencil size={14} /> Edit
                      </button>
                      <button
                        type="button"
                        className="btn-quiet"
                        style={{ minHeight: 0, padding: "6px 8px" }}
                        onClick={() => void toggleActive(account)}
                        disabled={busyId === account.id}
                        aria-label={account.is_active ? `Deactivate ${account.account_name}` : `Reactivate ${account.account_name}`}
                      >
                        {busyId === account.id ? <Loader2 className="spin" size={14} /> : <Power size={14} />}
                        {account.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {visible.length === 0 && (
            <p style={{ margin: "16px 0 0", color: "#6B6860", fontSize: 13 }}>No accounts match this search.</p>
          )}
        </section>
      )}
    </DashboardLayout>
  );
}
