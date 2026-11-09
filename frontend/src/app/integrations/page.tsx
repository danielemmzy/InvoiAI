"use client";
import { useEffect, useState } from "react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useIntegrations, useSyncChartOfAccounts } from "@/hooks/useAP";
import { accountingTaxMappingsApi, integrationsApi, type AccountingTaxMapping } from "@/api/ap";
import { ArrowRight, CheckCircle2, PlugZap, RefreshCw, Trash2 } from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";

export default function IntegrationsPage() {
  const q = useIntegrations(); const sync = useSyncChartOfAccounts();
  const qb = q.data?.find((x: any) => String(x.provider || "").toLowerCase() === "quickbooks");
  const [mappings, setMappings] = useState<AccountingTaxMapping[]>([]);
  const [provider, setProvider] = useState<"quickbooks" | "xero">("quickbooks");
  const [rate, setRate] = useState("0"); const [sourceCode, setSourceCode] = useState("");
  const [externalId, setExternalId] = useState(""); const [externalName, setExternalName] = useState("");
  const [busy, setBusy] = useState(false);
  async function reloadMappings() { try { setMappings(await accountingTaxMappingsApi.list()); } catch { /* Migration may not yet be applied. */ } }
  useEffect(() => { void reloadMappings(); }, []);
  async function saveMapping(e: React.FormEvent) {
    e.preventDefault(); const parsed = Number(rate);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100 || !externalId.trim()) { toast.error("Enter a valid tax rate and external tax-code ID."); return; }
    setBusy(true); try { await accountingTaxMappingsApi.save({ provider, source_tax_rate: parsed, source_tax_code: sourceCode.trim() || null, external_tax_code_id: externalId.trim(), external_tax_code_name: externalName.trim() || null }); toast.success("Tax mapping saved."); setExternalId(""); setExternalName(""); await reloadMappings(); } catch (err: any) { toast.error(err?.response?.data?.detail || "Could not save tax mapping. Check that the tax-mapping migration is applied."); } finally { setBusy(false); }
  }
  async function deactivate(id: string) { try { await accountingTaxMappingsApi.deactivate(id); toast.success("Mapping deactivated."); await reloadMappings(); } catch { toast.error("Could not deactivate mapping."); } }
  return <DashboardLayout><div className="page-head"><div><div className="eyebrow">Connections</div><h1 className="page-title">Integrations</h1><p className="page-subtitle">Connect accounting systems and configure provider-specific tax mappings. Credentials remain on the backend.</p></div></div>
    <div className="integration-grid"><div className="panel integration-card"><div className="integration-icon"><PlugZap/></div><div><div className="eyebrow">Accounting</div><h2>QuickBooks</h2><p>{qb ? "Connected and available for sync." : "Connect QuickBooks to import your Chart of Accounts and send approved bills."}</p></div><div className="integration-actions">{qb ? <><span className="connected"><CheckCircle2 size={15}/> Connected</span><button className="btn-secondary" onClick={() => sync.mutate()} disabled={sync.isPending}>{sync.isPending ? <RefreshCw className="spin" size={15}/> : <RefreshCw size={15}/>} Sync accounts</button><Link href="/dashboard/ap" className="text-link">Open AP <ArrowRight size={14}/></Link></> : <a className="btn-primary" href={integrationsApi.connectQuickBooks()}>Connect QuickBooks <ArrowRight size={15}/></a>}</div></div></div>
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
