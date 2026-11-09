"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useIntegrations, useSyncChartOfAccounts, useSyncSuppliers } from "@/hooks/useAP";
import { accountingTaxMappingsApi, integrationsApi, type AccountingTaxMapping, type IntegrationProvider } from "@/api/ap";
import { ArrowRight, CheckCircle2, PlugZap, RefreshCw, Trash2, UsersRound } from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";
import { getErrorMessage } from "@/api/client";
import { useAppStore } from "@/store/useAppStore";
import { readSupplierImportSummary } from "@/lib/supplierSync";

export default function IntegrationsPage() {
  const q = useIntegrations(); const sync = useSyncChartOfAccounts(); const supplierSync = useSyncSuppliers();
  const queryClient = useQueryClient();
  const workspaceId = useAppStore((state) => state.activeWorkspace?.id);
  const qb = q.data?.find((connection) => connection.provider.toLowerCase() === "quickbooks");
  const activeAccountingConnections = (q.data ?? []).filter((connection) => connection.is_active && ["quickbooks", "xero", "sage"].includes(connection.provider));
  const mappingsQuery = useQuery({ queryKey: ["accounting-tax-mappings", workspaceId], queryFn: () => accountingTaxMappingsApi.list(), enabled: !!workspaceId });
  const mappings: AccountingTaxMapping[] = mappingsQuery.data ?? [];
  const [provider, setProvider] = useState<"quickbooks" | "xero">("quickbooks");
  const [rate, setRate] = useState("0"); const [sourceCode, setSourceCode] = useState("");
  const [externalId, setExternalId] = useState(""); const [externalName, setExternalName] = useState("");
  const [busy, setBusy] = useState(false);
  const reloadMappings = () => queryClient.invalidateQueries({ queryKey: ["accounting-tax-mappings", workspaceId] });
  async function saveMapping(e: React.FormEvent) {
    e.preventDefault(); const parsed = Number(rate);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100 || !externalId.trim()) { toast.error("Enter a valid tax rate and external tax-code ID."); return; }
    setBusy(true); try { await accountingTaxMappingsApi.save({ provider, source_tax_rate: parsed, source_tax_code: sourceCode.trim() || null, external_tax_code_id: externalId.trim(), external_tax_code_name: externalName.trim() || null }); toast.success("Tax mapping saved."); setExternalId(""); setExternalName(""); await reloadMappings(); } catch (err: unknown) { toast.error(getErrorMessage(err, "Could not save tax mapping. Check that the tax-mapping migration is applied.")); } finally { setBusy(false); }
  }
  async function deactivate(id: string) { try { await accountingTaxMappingsApi.deactivate(id); toast.success("Mapping deactivated."); await reloadMappings(); } catch (err: unknown) { toast.error(getErrorMessage(err, "Could not deactivate mapping.")); } }
  return <DashboardLayout><div className="page-head"><div><div className="eyebrow">Connections</div><h1 className="page-title">Integrations</h1><p className="page-subtitle">Connect accounting systems and configure provider-specific tax mappings. Credentials remain on the backend.</p></div></div>
    <div className="integration-grid"><div className="panel integration-card"><div className="integration-icon"><PlugZap/></div><div><div className="eyebrow">Accounting</div><h2>QuickBooks</h2><p>{qb ? "Connected and available for sync." : "Connect QuickBooks to import your Chart of Accounts and send approved bills."}</p></div><div className="integration-actions">{qb ? <><span className="connected"><CheckCircle2 size={15}/> Connected</span><button className="btn-secondary" onClick={() => sync.mutate()} disabled={sync.isPending}>{sync.isPending ? <RefreshCw className="spin" size={15}/> : <RefreshCw size={15}/>} Sync accounts</button><Link href="/dashboard/ap" className="text-link">Open AP <ArrowRight size={14}/></Link></> : <a className="btn-primary" href={integrationsApi.connectQuickBooks()}>Connect QuickBooks <ArrowRight size={15}/></a>}</div></div></div>
    <section className="panel" style={{ marginTop: 24, padding: 24 }} aria-labelledby="supplier-import-title">
      <div className="eyebrow">Accounts payable</div><h2 id="supplier-import-title">Supplier import</h2>
      <p className="page-subtitle">Import supplier contacts from the selected accounting connection. InvoiAI only links local records; it does not create suppliers in your accounting system.</p>
      {!activeAccountingConnections.length ? <p role="status" style={{ marginTop: 16 }}>No active accounting connection. You can still create and manage suppliers in InvoiAI.</p> : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: 16, marginTop: 16 }}>
          {activeAccountingConnections.map((connection) => {
            const summary = readSupplierImportSummary(connection.metadata);
            const label = connection.provider === "quickbooks" ? "QuickBooks Online" : connection.provider === "xero" ? "Xero" : "Sage Accounting";
            return <article key={connection.id} className="integration-card" style={{ alignItems: "flex-start" }}>
              <div className="integration-icon"><UsersRound aria-hidden="true" /></div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="eyebrow">{label}</div><h3>{connection.account_name || "Connected account"}</h3>
                {connection.provider === "sage" ? <p role="status">Supplier import is unavailable until the Sage Contacts connector is verified.</p> : <button className="btn-secondary" style={{ minHeight: 44, marginTop: 8 }} onClick={() => supplierSync.mutate(connection.provider as IntegrationProvider)} disabled={supplierSync.isPending}>
                  {supplierSync.isPending && supplierSync.variables === connection.provider ? <RefreshCw className="spin" size={15} aria-hidden="true" /> : <RefreshCw size={15} aria-hidden="true" />}
                  {supplierSync.isPending && supplierSync.variables === connection.provider ? "Importing suppliers…" : "Import suppliers"}
                </button>}
                {summary ? <div aria-live="polite" style={{ marginTop: 16 }}>
                  <p><strong>Last import:</strong> {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(summary.completedAt))}</p>
                  <p>{summary.counts.total} read · {summary.counts.imported} added · {summary.counts.updated} updated · {summary.counts.skipped} skipped · {summary.counts.failed} failed</p>
                  {summary.errors.length ? <div role="alert" style={{ marginTop: 8 }}><strong>Supplier import errors</strong><ul>{summary.errors.map((error, index) => <li key={`${error.external_id || error.resource}-${index}`}>{error.resource}{error.external_id ? ` ${error.external_id}` : ""}: {error.error}</li>)}</ul></div> : <p role="status">No supplier import errors.</p>}
                </div> : <p style={{ marginTop: 12 }}>No supplier import has run for this connection.</p>}
              </div>
            </article>;
          })}
        </div>
      )}
    </section>
    <section className="panel" style={{ marginTop: 24, padding: 24 }}><div className="eyebrow">Accounts payable</div><h2>Tax-code mappings</h2><p className="page-subtitle">Map the invoice tax rate/code to the corresponding tax code in each accounting provider. Use the external ID from your provider. Apply the database migration before saving.</p>
      <form onSubmit={saveMapping} style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))", gap:12, marginTop:16 }}>
        <label>Provider<select className="input" value={provider} onChange={e=>setProvider(e.target.value as "quickbooks"|"xero")}><option value="quickbooks">QuickBooks</option><option value="xero">Xero</option></select></label>
        <label>Source tax rate (%)<input className="input" type="number" min="0" max="100" step="0.0001" value={rate} onChange={e=>setRate(e.target.value)} required /></label>
        <label>Source tax code (optional)<input className="input" value={sourceCode} onChange={e=>setSourceCode(e.target.value)} placeholder="e.g. VAT-7.5" /></label>
        <label>Provider tax-code ID<input className="input" value={externalId} onChange={e=>setExternalId(e.target.value)} required placeholder="External ID" /></label>
        <label>Provider tax-code name<input className="input" value={externalName} onChange={e=>setExternalName(e.target.value)} placeholder="e.g. Standard VAT" /></label>
        <div style={{ display:"flex", alignItems:"end" }}><button className="btn-primary" type="submit" disabled={busy}>{busy ? "Saving…" : "Save mapping"}</button></div>
      </form>
      <div style={{ overflowX:"auto", marginTop:20 }}><table style={{ width:"100%", borderCollapse:"collapse" }}><thead><tr><th align="left">Provider</th><th align="left">Source rate</th><th align="left">Source code</th><th align="left">External tax code</th><th align="left">Status</th><th></th></tr></thead><tbody>{mappings.map(m=><tr key={m.id}><td>{m.provider}</td><td>{m.source_tax_rate}%</td><td>{m.source_tax_code || "—"}</td><td>{m.external_tax_code_name || m.external_tax_code_id}</td><td>{m.is_active ? "Active" : "Inactive"}</td><td>{m.is_active && <button className="btn-secondary" onClick={()=>void deactivate(m.id)} aria-label="Deactivate mapping"><Trash2 size={14}/></button>}</td></tr>)}{!mappings.length && <tr><td colSpan={6} style={{ padding:16, opacity:.7 }}>No tax mappings loaded yet. If you have existing mappings, check that the migration is applied and reload.</td></tr>}</tbody></table></div>
      <p style={{ marginTop:16, fontSize:13, opacity:.8 }}>Safety note: this configuration screen does not itself prove that a provider will accept a tax code or calculate the expected total. Verify both providers in their sandbox before using taxable bills in production.</p>
    </section></DashboardLayout>;
}
