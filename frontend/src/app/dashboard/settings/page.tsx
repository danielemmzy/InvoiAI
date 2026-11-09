"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity, Bell, Bot, Building2, Check, ChevronDown, ChevronRight, CircleUserRound,
  CreditCard, Database, ExternalLink, FileInput, GitCompareArrows, KeyRound,
  Loader2, LockKeyhole, Palette, ReceiptText, Save, Settings2, ShieldCheck,
  Users, WalletCards, Webhook, X,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/store/useAppStore";
import { getErrorMessage } from "@/api/client";
import { settingsApi, OrganizationSettingsResponse } from "@/api/settings";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DOC_TYPES = ["invoice", "credit_note", "debit_note", "receipt", "purchase_order", "goods_receipt"];

function getPath(obj: Record<string, unknown>, path: string, fallback: unknown = "") {
  return path.split(".").reduce<unknown>((value, key) => (value && typeof value === "object" ? (value as Record<string, unknown>)[key] : undefined), obj) ?? fallback;
}

function setPath(obj: Record<string, unknown>, path: string, value: unknown) {
  const keys = path.split(".");
  let cursor = obj;
  keys.slice(0, -1).forEach((key) => {
    if (!cursor[key] || typeof cursor[key] !== "object") cursor[key] = {};
    cursor = cursor[key] as Record<string, unknown>;
  });
  cursor[keys[keys.length - 1]] = value;
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

type SectionProps = { title: string; description: string; children: React.ReactNode; open?: boolean };
function Section({ title, description, children, open = true }: SectionProps) {
  const [expanded, setExpanded] = useState(open);
  return (
    <div className="settings-panel-card">
      <button type="button" onClick={() => setExpanded((v) => !v)} className="settings-panel-head">
        <div>
          <div className="settings-panel-title">{title}</div>
          <div className="settings-sub" style={{ marginTop: 5 }}>{description}</div>
        </div>
        <span className={`settings-collapse ${expanded ? "is-open" : ""}`}><ChevronDown size={16} /></span>
      </button>
      {expanded && <div className="settings-panel-body">{children}</div>}
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="settings-field">
      <div className="settings-field-copy">
        <div className="settings-key">{label}</div>
        {hint && <div className="settings-sub">{hint}</div>}
      </div>
      <div className="settings-field-control">{children}</div>
    </div>
  );
}

function Input({ value, onChange, type = "text", min, max, step }: { value: string | number | undefined; onChange: (v: string) => void; type?: string; min?: number; max?: number; step?: number }) {
  return <input className="settings-control" type={type} value={value ?? ""} min={min} max={max} step={step} onChange={(e) => onChange(e.target.value)} style={{ width: "100%" }} />;
}

function Select({ value, onChange, options }: { value: string | number | undefined; onChange: (v: string) => void; options: { value: string; label: string }[] }) {
  return (
    <div className="settings-select-wrap">
      <select className="settings-control settings-select" value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      <ChevronDown size={15} aria-hidden="true" />
    </div>
  );
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button type="button" role="switch" aria-checked={Boolean(value)} className={`settings-switch ${value ? "is-on" : ""}`} onClick={() => onChange(!value)}>
      <span>{value ? "On" : "Off"}</span>
      <span className="settings-switch-knob"><Check size={11} strokeWidth={3} /></span>
    </button>
  );
}

function LinkCard({ title, description, href }: { title: string; description: string; href: string }) {
  return (
    <a href={href} className="settings-link-card">
      <span className="settings-link-icon"><ExternalLink size={15} /></span>
      <span style={{ flex: 1 }}><span className="settings-key">{title}</span><span className="settings-sub">{description}</span></span>
      <ChevronRight size={16} className="settings-link-arrow" />
    </a>
  );
}

export default function SettingsPage() {
  const { user } = useAppStore();
  const { logout } = useAuth();
  const [data, setData] = useState<OrganizationSettingsResponse | null>(null);
  const [draft, setDraft] = useState<OrganizationSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [activeSection, setActiveSection] = useState("ap");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const canUpdate = useMemo(() => Boolean(data?.permissions.includes("settings:update")), [data]);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const result = await settingsApi.get();
      setData(result); setDraft(clone(result));
    } catch (e) { setError(getErrorMessage(e, "Unable to load organization settings.")); }
    finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, []);

  const updateOrg = (key: string, value: unknown) => setDraft((current) => current ? ({ ...current, organization: { ...current.organization, [key]: value } }) : current);
  const updateSetting = (key: string, value: unknown) => setDraft((current) => current ? ({ ...current, settings: { ...current.settings, [key]: value } }) : current);
  const updatePolicy = (path: string, value: unknown) => setDraft((current) => {
    if (!current) return current;
    const next = clone(current);
    setPath(next.settings.policy_settings, path, value);
    return next;
  });
  const policy = (path: string, fallback: unknown = "") => draft ? getPath(draft.settings.policy_settings, path, fallback) : fallback;

  const save = async () => {
    if (!draft || !canUpdate) return;
    setSaving(true); setSaved(false); setError(null);
    try {
      const result = await settingsApi.update({
        organization: {
          name: draft.organization.name,
          industry: draft.organization.industry,
          company_size: draft.organization.company_size,
          country: draft.organization.country,
          currency: draft.organization.currency,
          website: draft.organization.website,
          logo_url: draft.organization.logo_url,
          tax_id: draft.organization.tax_id,
        },
        settings: {
          default_currency: draft.settings.default_currency,
          supported_currencies: draft.settings.supported_currencies,
          timezone: draft.settings.timezone,
          fiscal_year_start_month: draft.settings.fiscal_year_start_month,
          date_format: draft.settings.date_format,
          number_format: draft.settings.number_format,
          default_language: draft.settings.default_language,
          auto_analyze: draft.settings.auto_analyze,
          ocr_language: draft.settings.ocr_language,
          default_industry: draft.settings.default_industry,
          supported_document_types: draft.settings.supported_document_types,
          duplicate_threshold: draft.settings.duplicate_threshold,
          duplicate_window_days: draft.settings.duplicate_window_days,
          duplicate_amount_tolerance: draft.settings.duplicate_amount_tolerance,
          fraud_sensitivity: draft.settings.fraud_sensitivity,
          auto_reject_fraud_score: draft.settings.auto_reject_fraud_score,
          fraud_alert_email: draft.settings.fraud_alert_email,
          auto_create_vendors: draft.settings.auto_create_vendors,
          vendor_match_threshold: draft.settings.vendor_match_threshold,
          require_vendor_verification: draft.settings.require_vendor_verification,
          ai_enabled: draft.settings.ai_enabled,
          ai_model_preference: draft.settings.ai_model_preference,
          ai_temperature: draft.settings.ai_temperature,
          enable_embeddings: draft.settings.enable_embeddings,
          copilot_enabled: draft.settings.copilot_enabled,
          copilot_memory_days: draft.settings.copilot_memory_days,
          copilot_max_context_docs: draft.settings.copilot_max_context_docs,
          analytics_enabled: draft.settings.analytics_enabled,
          analytics_retention_months: draft.settings.analytics_retention_months,
          email_notifications: draft.settings.email_notifications,
          notification_email: draft.settings.notification_email,
          slack_webhook_url: draft.settings.slack_webhook_url,
          outbound_webhook_url: draft.settings.outbound_webhook_url,
          brand_color: draft.settings.brand_color,
          custom_domain: draft.settings.custom_domain,
          sso_provider: draft.settings.sso_provider,
          sso_config: draft.settings.sso_config,
        },
        policy_settings: draft.settings.policy_settings,
      });
      setData(result); setDraft(clone(result)); setSaved(true);
    } catch (e) { setError(getErrorMessage(e, "Unable to save settings.")); }
    finally { setSaving(false); }
  };

  if (loading) return <DashboardLayout><div className="dash-page-header"><div className="section-label">§04 Account / Settings</div><div className="dash-title serif">Settings</div></div><div className="card" style={{ padding: 24 }}>Loading organization settings...</div></DashboardLayout>;
  if (!draft) return <DashboardLayout><div className="dash-page-header"><div className="dash-title serif">Settings</div></div><div className="card" style={{ padding: 24 }}>{error || "Settings are unavailable."}</div></DashboardLayout>;

  const p = (path: string, fallback: unknown = "") => policy(path, fallback);
  const setP = updatePolicy;

  const navItems = [
    { id: "general", label: "General", short: "Workspace", icon: Building2, description: "Organization identity, locale and document defaults." },
    { id: "ap", label: "Accounts Payable", short: "AP", icon: ReceiptText, description: "AP automation, routing and invoice controls." },
    { id: "intake", label: "Invoice Intake", short: "Intake", icon: FileInput, description: "How invoices enter InvoiAI and become payable work." },
    { id: "matching", label: "Matching & Exceptions", short: "Matching", icon: GitCompareArrows, description: "2-way / 3-way matching, tolerances and exceptions." },
    { id: "risk", label: "Risk & Vendors", short: "Risk", icon: ShieldCheck, description: "Duplicate, fraud and vendor protection." },
    { id: "accounting", label: "Accounting & Tax", short: "Accounting", icon: Database, description: "Coding, GL validation and tax policy." },
    { id: "approvals", label: "Approvals", short: "Approvals", icon: Users, description: "Approval authority, routing and escalation." },
    { id: "payments", label: "Payments", short: "Payments", icon: WalletCards, description: "Payment authorization and release controls." },
    { id: "ai", label: "AI & Intelligence", short: "AI", icon: Bot, description: "AI extraction, confidence and Copilot." },
    { id: "notifications", label: "Notifications", short: "Alerts", icon: Bell, description: "Approval, exception and payment alerts." },
    { id: "integrations", label: "Integrations", short: "ERP", icon: Webhook, description: "ERP sync and export gates." },
    { id: "security", label: "Security & Access", short: "Security", icon: LockKeyhole, description: "MFA, roles, authority and segregation of duties." },
    { id: "audit", label: "Audit & Retention", short: "Audit", icon: Activity, description: "Audit logging, retention and analytics." },
    { id: "branding", label: "Branding", short: "Brand", icon: Palette, description: "Vendor experience and organization presentation." },
    { id: "enterprise", label: "SSO & Enterprise", short: "SSO", icon: KeyRound, description: "Enterprise authentication configuration." },
    { id: "account", label: "Account & Billing", short: "Account", icon: CircleUserRound, description: "Plan, account and product-level links." },
  ] as const;

  const active = navItems.find((item) => item.id === activeSection) ?? navItems[1];

  const goTo = (id: string) => { setActiveSection(id); setMobileNavOpen(false); window.scrollTo({ top: 0, behavior: "smooth" }); };

  return <DashboardLayout>
    <div className="settings-shell">
      <div className="settings-hero">
        <div>
          <div className="section-label">§04 ACCOUNT / SETTINGS</div>
          <div className="settings-title-row">
            <div>
              <h1 className="settings-page-title serif">Settings center</h1>
              <p className="settings-page-subtitle">One control surface for how InvoiAI receives, validates, approves and pays invoices.</p>
            </div>
            <div className="settings-status-chip"><span className={`settings-status-dot ${canUpdate ? "live" : "readonly"}`} />{canUpdate ? "Organization controls" : "Read only"}</div>
          </div>
        </div>
      </div>

      <div className="settings-tabbar">
        <div className="settings-tabbar-mobile">
          <button type="button" className="settings-mobile-select" onClick={() => setMobileNavOpen((v) => !v)}>
            <span>{active.label}</span><ChevronDown size={16} className={mobileNavOpen ? "rotate-180" : ""} />
          </button>
          {mobileNavOpen && <div className="settings-mobile-menu">{navItems.map((item) => <button key={item.id} type="button" className={item.id === activeSection ? "is-active" : ""} onClick={() => goTo(item.id)}>{item.short}<ChevronRight size={14} /></button>)}</div>}
        </div>
        <div className="settings-tabs">
          {navItems.map((item) => {
            const Icon = item.icon;
            return <button key={item.id} type="button" className={`settings-tab ${item.id === activeSection ? "is-active" : ""}`} onClick={() => goTo(item.id)} title={item.description}>
              <Icon size={15} /> <span>{item.short}</span>
            </button>;
          })}
        </div>
      </div>

      <div className="settings-workspace">
        <aside className="settings-sidebar">
          <div className="settings-sidebar-caption">SETTINGS</div>
          <div className="settings-sidebar-current">
            <span className="settings-current-icon"><Settings2 size={16} /></span>
            <span><strong>{active.label}</strong><small>{active.description}</small></span>
          </div>
          <div className="settings-sidebar-list">
            {navItems.map((item) => <button key={item.id} type="button" className={item.id === activeSection ? "is-active" : ""} onClick={() => goTo(item.id)}>{item.short}<ChevronRight size={14} /></button>)}
          </div>
        </aside>

        <main className="settings-content">
          <div className="settings-content-head">
            <div>
              <div className="settings-eyebrow">{active.short}</div>
              <h2 className="settings-section-title serif">{active.label}</h2>
              <p>{active.description}</p>
            </div>
            <div className="settings-savebar">
              {saved ? <span className="settings-saved"><Check size={14} /> Saved</span> : <span className="settings-savehint">{canUpdate ? "Changes stay local until you save." : "Read-only access."}</span>}
              {canUpdate && <button className="settings-save-button" onClick={() => void save()} disabled={saving}>{saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}{saving ? "Saving" : "Save changes"}</button>}
            </div>
          </div>
          {error && <div className="settings-error"><X size={15} />{error}</div>}

      {activeSection === "general" && ( <Section title="General & Organization" description="Company identity, localization, fiscal year and document defaults.">
        <Field label="Organization name"><Input value={draft.organization.name} onChange={(v) => updateOrg("name", v)} /></Field>
        <Field label="Industry"><Input value={draft.organization.industry || ""} onChange={(v) => updateOrg("industry", v)} /></Field>
        <Field label="Company size"><Select value={draft.organization.company_size || ""} onChange={(v) => updateOrg("company_size", v)} options={["", "1-10", "11-50", "51-200", "201-500", "501-1000", "1001+"].map((v) => ({ value: v, label: v || "Not specified" }))} /></Field>
        <Field label="Country"><Input value={draft.organization.country || ""} onChange={(v) => updateOrg("country", v)} /></Field>
        <Field label="Tax ID"><Input value={draft.organization.tax_id || ""} onChange={(v) => updateOrg("tax_id", v)} /></Field>
        <Field label="Website"><Input value={draft.organization.website || ""} onChange={(v) => updateOrg("website", v)} /></Field>
        <Field label="Default currency"><Input value={draft.settings.default_currency} onChange={(v) => updateSetting("default_currency", v.toUpperCase())} /></Field>
        <Field label="Supported currencies" hint="Comma-separated ISO currency codes."><Input value={draft.settings.supported_currencies.join(", ")} onChange={(v) => updateSetting("supported_currencies", v.split(",").map((x) => x.trim().toUpperCase()).filter(Boolean))} /></Field>
        <Field label="Timezone"><Input value={draft.settings.timezone} onChange={(v) => updateSetting("timezone", v)} /></Field>
        <Field label="Fiscal year start"><Select value={draft.settings.fiscal_year_start_month} onChange={(v) => updateSetting("fiscal_year_start_month", Number(v))} options={MONTHS.map((m, i) => ({ value: String(i + 1), label: m }))} /></Field>
        <Field label="Date format"><Select value={draft.settings.date_format} onChange={(v) => updateSetting("date_format", v)} options={["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"].map((v) => ({ value: v, label: v }))} /></Field>
        <Field label="Number format"><Select value={draft.settings.number_format} onChange={(v) => updateSetting("number_format", v)} options={["1,234.56", "1.234,56", "1 234,56"].map((v) => ({ value: v, label: v }))} /></Field>
        <Field label="Default language"><Input value={draft.settings.default_language} onChange={(v) => updateSetting("default_language", v)} /></Field>
        <Field label="Automatic document analysis"><Toggle value={draft.settings.auto_analyze} onChange={(v) => updateSetting("auto_analyze", v)} /></Field>
        <Field label="OCR language"><Input value={draft.settings.ocr_language} onChange={(v) => updateSetting("ocr_language", v)} /></Field>
        <Field label="Supported document types"><Input value={draft.settings.supported_document_types.join(", ")} onChange={(v) => updateSetting("supported_document_types", v.split(",").map((x) => x.trim()).filter((x) => DOC_TYPES.includes(x)))} /></Field>
      </Section>
      )}


      {activeSection === "ap" && ( <Section title="Accounts Payable" description="Core AP automation, intake, workflow and non-PO policy.">
        <Field label="Accounts Payable enabled"><Toggle value={Boolean(p("ap.enabled", true))} onChange={(v) => setP("ap.enabled", v)} /></Field>
        <Field label="Default AP workflow"><Select value={String(p("ap.default_workflow", "auto"))} onChange={(v) => setP("ap.default_workflow", v)} options={["auto", "manual", "straight_through"].map((v) => ({ value: v, label: v.replace("_", " ") }))} /></Field>
        <Field label="Default matching mode"><Select value={String(p("ap.default_match_mode", "auto"))} onChange={(v) => setP("ap.default_match_mode", v)} options={["auto", "non_po", "two_way", "three_way"].map((v) => ({ value: v, label: v.replace("_", " ") }))} /></Field>
        <Field label="Allow Non-PO invoices"><Toggle value={Boolean(p("ap.allow_non_po", true))} onChange={(v) => setP("ap.allow_non_po", v)} /></Field>
        <Field label="Require PO above amount"><Input type="number" value={Number(p("ap.require_po_above_amount", 0))} onChange={(v) => setP("ap.require_po_above_amount", Number(v))} min={0} /></Field>
        <Field label="Require approval for all invoices"><Toggle value={Boolean(p("ap.require_approval_all", true))} onChange={(v) => setP("ap.require_approval_all", v)} /></Field>
        <Field label="Auto-submit after validation"><Toggle value={Boolean(p("ap.auto_submit", true))} onChange={(v) => setP("ap.auto_submit", v)} /></Field>
        <Field label="Auto-match invoices"><Toggle value={Boolean(p("ap.auto_match", true))} onChange={(v) => setP("ap.auto_match", v)} /></Field>
        <Field label="Auto-code invoices"><Toggle value={Boolean(p("ap.auto_code", true))} onChange={(v) => setP("ap.auto_code", v)} /></Field>
        <Field label="Manual review on low confidence"><Toggle value={Boolean(p("ap.manual_review_on_low_confidence", true))} onChange={(v) => setP("ap.manual_review_on_low_confidence", v)} /></Field>
      </Section>
      )}


      {activeSection === "intake" && ( <Section title="Invoice Intake" description="Control how emailed and uploaded invoices enter AP.">
        <Field label="AP email intake"><Toggle value={Boolean(p("ap.invoice_intake.email_enabled", true))} onChange={(v) => setP("ap.invoice_intake.email_enabled", v)} /></Field>
        <Field label="Accepted document types"><Input value={String((p("ap.invoice_intake.accepted_document_types", []) as string[]).join(", "))} onChange={(v) => setP("ap.invoice_intake.accepted_document_types", v.split(",").map((x) => x.trim()).filter(Boolean))} /></Field>
        <Field label="Auto-classify documents"><Toggle value={Boolean(p("ap.invoice_intake.auto_classify", true))} onChange={(v) => setP("ap.invoice_intake.auto_classify", v)} /></Field>
        <Field label="Require invoice number"><Toggle value={Boolean(p("ap.invoice_intake.require_invoice_number", true))} onChange={(v) => setP("ap.invoice_intake.require_invoice_number", v)} /></Field>
        <Field label="Require vendor"><Toggle value={Boolean(p("ap.invoice_intake.require_vendor", true))} onChange={(v) => setP("ap.invoice_intake.require_vendor", v)} /></Field>
        <Field label="Require currency"><Toggle value={Boolean(p("ap.invoice_intake.require_currency", true))} onChange={(v) => setP("ap.invoice_intake.require_currency", v)} /></Field>
        <Field label="Require invoice date"><Toggle value={Boolean(p("ap.invoice_intake.require_invoice_date", true))} onChange={(v) => setP("ap.invoice_intake.require_invoice_date", v)} /></Field>
        <Field label="Require due date"><Toggle value={Boolean(p("ap.invoice_intake.require_due_date", false))} onChange={(v) => setP("ap.invoice_intake.require_due_date", v)} /></Field>
        <Field label="Require line items"><Toggle value={Boolean(p("ap.invoice_intake.require_line_items", false))} onChange={(v) => setP("ap.invoice_intake.require_line_items", v)} /></Field>
      </Section>
      )}


      {activeSection === "matching" && ( <Section title="Matching & Exceptions" description="2-way/3-way matching tolerances and exception behavior.">
        <Field label="2-way matching"><Toggle value={Boolean(p("ap.matching.two_way_enabled", true))} onChange={(v) => setP("ap.matching.two_way_enabled", v)} /></Field>
        <Field label="3-way matching"><Toggle value={Boolean(p("ap.matching.three_way_enabled", true))} onChange={(v) => setP("ap.matching.three_way_enabled", v)} /></Field>
        <Field label="Quantity tolerance %"><Input type="number" value={Number(p("ap.matching.quantity_tolerance_percent", 0))} onChange={(v) => setP("ap.matching.quantity_tolerance_percent", Number(v))} min={0} /></Field>
        <Field label="Price tolerance %"><Input type="number" value={Number(p("ap.matching.price_tolerance_percent", 0))} onChange={(v) => setP("ap.matching.price_tolerance_percent", Number(v))} min={0} /></Field>
        <Field label="Amount tolerance"><Input type="number" value={Number(p("ap.matching.amount_tolerance", 0))} onChange={(v) => setP("ap.matching.amount_tolerance", Number(v))} min={0} /></Field>
        <Field label="Tax tolerance"><Input type="number" value={Number(p("ap.matching.tax_tolerance", 0))} onChange={(v) => setP("ap.matching.tax_tolerance", Number(v))} min={0} /></Field>
        {(["currency_mismatch_action", "vendor_mismatch_action", "missing_po_action", "missing_receipt_action", "partial_receipt_action", "over_invoice_action", "under_invoice_action", "closed_po_action"] as const).map((key) => <Field key={key} label={key.replaceAll("_", " ")}><Select value={String(p(`ap.matching.${key}`, "exception"))} onChange={(v) => setP(`ap.matching.${key}`, v)} options={["block", "exception", "warning", "allow"].map((v) => ({ value: v, label: v }))} /></Field>)}
        <Field label="Default exception action"><Select value={String(p("ap.exceptions.default_action", "route_to_ap"))} onChange={(v) => setP("ap.exceptions.default_action", v)} options={["route_to_ap", "route_to_supervisor", "route_to_requester", "block", "warning"].map((v) => ({ value: v, label: v }))} /></Field>
        <Field label="Auto-hold exceptions"><Toggle value={Boolean(p("ap.exceptions.auto_hold", true))} onChange={(v) => setP("ap.exceptions.auto_hold", v)} /></Field>
        <Field label="Resolve exceptions before payment"><Toggle value={Boolean(p("ap.exceptions.require_resolution_before_payment", true))} onChange={(v) => setP("ap.exceptions.require_resolution_before_payment", v)} /></Field>
        <Field label="Escalate exceptions after hours"><Input type="number" value={Number(p("ap.exceptions.escalation_hours", 72))} onChange={(v) => setP("ap.exceptions.escalation_hours", Number(v))} min={1} /></Field>
      </Section>
      )}


      {activeSection === "risk" && ( <Section title="Duplicate Detection & Fraud" description="Prevent duplicate invoices and route high-risk transactions.">
        <Field label="Duplicate detection"><Toggle value={Boolean(p("duplicate_detection.enabled", true))} onChange={(v) => setP("duplicate_detection.enabled", v)} /></Field>
        <Field label="Duplicate similarity threshold %"><Input type="number" value={Number(p("duplicate_detection.threshold", draft.settings.duplicate_threshold))} onChange={(v) => { setP("duplicate_detection.threshold", Number(v)); updateSetting("duplicate_threshold", Number(v)); }} min={0} max={100} /></Field>
        <Field label="Duplicate lookback days"><Input type="number" value={Number(p("duplicate_detection.window_days", draft.settings.duplicate_window_days))} onChange={(v) => { setP("duplicate_detection.window_days", Number(v)); updateSetting("duplicate_window_days", Number(v)); }} min={1} /></Field>
        <Field label="Duplicate amount tolerance"><Input type="number" value={Number(p("duplicate_detection.amount_tolerance", draft.settings.duplicate_amount_tolerance))} onChange={(v) => { setP("duplicate_detection.amount_tolerance", Number(v)); updateSetting("duplicate_amount_tolerance", Number(v)); }} min={0} /></Field>
        <Field label="Duplicate action"><Select value={String(p("duplicate_detection.action", "block_payment"))} onChange={(v) => setP("duplicate_detection.action", v)} options={["block_payment", "route_to_ap", "warning"].map((v) => ({ value: v, label: v }))} /></Field>
        <Field label="Fraud detection"><Toggle value={Boolean(p("fraud.enabled", true))} onChange={(v) => setP("fraud.enabled", v)} /></Field>
        <Field label="Fraud sensitivity"><Select value={String(p("fraud.sensitivity", draft.settings.fraud_sensitivity))} onChange={(v) => { setP("fraud.sensitivity", v); updateSetting("fraud_sensitivity", v); }} options={["low", "medium", "high"].map((v) => ({ value: v, label: v }))} /></Field>
        <Field label="Auto-block fraud score"><Input type="number" value={Number(p("fraud.auto_block_score", draft.settings.auto_reject_fraud_score))} onChange={(v) => { setP("fraud.auto_block_score", Number(v)); updateSetting("auto_reject_fraud_score", Number(v)); }} min={0} max={100} /></Field>
        <Field label="Fraud alert email"><Input value={String(p("fraud.alert_email", draft.settings.fraud_alert_email || ""))} onChange={(v) => { setP("fraud.alert_email", v || null); updateSetting("fraud_alert_email", v || null); }} /></Field>
        <Field label="Review new bank accounts"><Toggle value={Boolean(p("fraud.new_bank_account_review", true))} onChange={(v) => setP("fraud.new_bank_account_review", v)} /></Field>
      </Section>
      )}


      {activeSection === "risk" && ( <Section title="Vendor Controls" description="Vendor onboarding, matching, verification and bank-change protection.">
        <Field label="Automatically create vendors"><Toggle value={draft.settings.auto_create_vendors} onChange={(v) => { updateSetting("auto_create_vendors", v); setP("vendor.auto_create", v); }} /></Field>
        <Field label="Vendor match threshold %"><Input type="number" value={Number(draft.settings.vendor_match_threshold)} onChange={(v) => { updateSetting("vendor_match_threshold", Number(v)); setP("vendor.match_threshold", Number(v)); }} min={0} max={100} /></Field>
        <Field label="Require vendor verification"><Toggle value={draft.settings.require_vendor_verification} onChange={(v) => { updateSetting("require_vendor_verification", v); setP("vendor.require_verification", v); }} /></Field>
        <Field label="Allow invoices from unverified vendors"><Toggle value={Boolean(p("vendor.allow_unverified_invoice", true))} onChange={(v) => setP("vendor.allow_unverified_invoice", v)} /></Field>
        <Field label="Block inactive vendors"><Toggle value={Boolean(p("vendor.block_inactive", true))} onChange={(v) => setP("vendor.block_inactive", v)} /></Field>
        <Field label="Require bank information"><Toggle value={Boolean(p("vendor.require_bank_information", true))} onChange={(v) => setP("vendor.require_bank_information", v)} /></Field>
        <Field label="Approval before first payment"><Toggle value={Boolean(p("vendor.require_approval_before_first_payment", true))} onChange={(v) => setP("vendor.require_approval_before_first_payment", v)} /></Field>
        <Field label="Independent bank-change verification"><Toggle value={Boolean(p("vendor.bank_change_independent_verification", true))} onChange={(v) => setP("vendor.bank_change_independent_verification", v)} /></Field>
      </Section>
      )}


      {activeSection === "accounting" && ( <Section title="Accounting, Coding & Tax" description="Automatic coding, GL controls and tax policy.">
        <Field label="Auto-coding"><Toggle value={Boolean(p("accounting.auto_coding", true))} onChange={(v) => { setP("accounting.auto_coding", v); updateSetting("ai_enabled", draft.settings.ai_enabled); }} /></Field>
        <Field label="Coding confidence threshold %"><Input type="number" value={Number(p("accounting.coding_confidence_threshold", 90))} onChange={(v) => setP("accounting.coding_confidence_threshold", Number(v))} min={0} max={100} /></Field>
        <Field label="Require coding approval"><Toggle value={Boolean(p("accounting.require_coding_approval", false))} onChange={(v) => setP("accounting.require_coding_approval", v)} /></Field>
        <Field label="Validate GL before export"><Toggle value={Boolean(p("accounting.validate_gl", true))} onChange={(v) => setP("accounting.validate_gl", v)} /></Field>
        <Field label="Department mapping"><Toggle value={Boolean(p("accounting.department_mapping", true))} onChange={(v) => setP("accounting.department_mapping", v)} /></Field>
        <Field label="Cost center mapping"><Toggle value={Boolean(p("accounting.cost_center_mapping", true))} onChange={(v) => setP("accounting.cost_center_mapping", v)} /></Field>
        <Field label="Tax enabled"><Toggle value={Boolean(p("accounting.tax_enabled", true))} onChange={(v) => setP("accounting.tax_enabled", v)} /></Field>
        <Field label="Tax-inclusive invoices"><Toggle value={Boolean(p("accounting.tax_inclusive_invoices", false))} onChange={(v) => setP("accounting.tax_inclusive_invoices", v)} /></Field>
        <Field label="Withholding tax"><Toggle value={Boolean(p("accounting.withholding_tax_enabled", false))} onChange={(v) => setP("accounting.withholding_tax_enabled", v)} /></Field>
        <Field label="Tax mismatch tolerance"><Input type="number" value={Number(p("accounting.tax_mismatch_tolerance", 0))} onChange={(v) => setP("accounting.tax_mismatch_tolerance", Number(v))} min={0} /></Field>
      </Section>
      )}


      {activeSection === "approvals" && ( <Section title="Approvals & Controls" description="Workflow authority, self-approval prevention, reminders and escalation.">
        <Field label="Prevent self-approval"><Toggle value={!Boolean(p("approvals.self_approval", false))} onChange={(v) => setP("approvals.self_approval", !v)} /></Field>
        <Field label="Processor cannot approve"><Toggle value={!Boolean(p("approvals.processor_can_approve", false))} onChange={(v) => setP("approvals.processor_can_approve", !v)} /></Field>
        <Field label="Vendor creator cannot approve"><Toggle value={!Boolean(p("approvals.vendor_creator_can_approve", false))} onChange={(v) => setP("approvals.vendor_creator_can_approve", !v)} /></Field>
        <Field label="Bank-change requester cannot approve"><Toggle value={!Boolean(p("approvals.bank_change_requester_can_approve", false))} onChange={(v) => setP("approvals.bank_change_requester_can_approve", !v)} /></Field>
        <Field label="Separate invoice/payment authorization"><Toggle value={!Boolean(p("approvals.invoice_approver_can_be_sole_payment_authorizer", false))} onChange={(v) => setP("approvals.invoice_approver_can_be_sole_payment_authorizer", !v)} /></Field>
        <Field label="Approval over authority"><Select value={String(p("approvals.approval_over_authority_action", "block"))} onChange={(v) => setP("approvals.approval_over_authority_action", v)} options={["block", "escalate", "warning"].map((v) => ({ value: v, label: v }))} /></Field>
        <Field label="First reminder after hours"><Input type="number" value={Number(p("approvals.reminder_after_hours", 24))} onChange={(v) => setP("approvals.reminder_after_hours", Number(v))} min={1} /></Field>
        <Field label="Second reminder after hours"><Input type="number" value={Number(p("approvals.second_reminder_after_hours", 48))} onChange={(v) => setP("approvals.second_reminder_after_hours", Number(v))} min={1} /></Field>
        <Field label="Escalate after hours"><Input type="number" value={Number(p("approvals.escalate_after_hours", 72))} onChange={(v) => setP("approvals.escalate_after_hours", Number(v))} min={1} /></Field>
        <Field label="Escalate to supervisor"><Toggle value={Boolean(p("approvals.escalate_to_supervisor", true))} onChange={(v) => setP("approvals.escalate_to_supervisor", v)} /></Field>
      </Section>
      )}


      {activeSection === "payments" && ( <Section title="Payments" description="Separate payment authorization and release controls from invoice approval.">
        <Field label="Payment approval required"><Toggle value={Boolean(p("payments.approval_required", true))} onChange={(v) => setP("payments.approval_required", v)} /></Field>
        <Field label="High-value payment threshold"><Input type="number" value={Number(p("payments.high_value_threshold", 0))} onChange={(v) => setP("payments.high_value_threshold", Number(v))} min={0} /></Field>
        <Field label="Dual authorization"><Toggle value={Boolean(p("payments.dual_authorization_enabled", true))} onChange={(v) => setP("payments.dual_authorization_enabled", v)} /></Field>
        <Field label="Payment batching"><Toggle value={Boolean(p("payments.payment_batching_enabled", true))} onChange={(v) => setP("payments.payment_batching_enabled", v)} /></Field>
        <Field label="Payment scheduling"><Toggle value={Boolean(p("payments.payment_scheduling_enabled", true))} onChange={(v) => setP("payments.payment_scheduling_enabled", v)} /></Field>
        <Field label="Hold on AP exception"><Toggle value={Boolean(p("payments.hold_on_exception", true))} onChange={(v) => setP("payments.hold_on_exception", v)} /></Field>
        <Field label="Hold on duplicate"><Toggle value={Boolean(p("payments.hold_on_duplicate", true))} onChange={(v) => setP("payments.hold_on_duplicate", v)} /></Field>
        <Field label="Hold on unverified vendor"><Toggle value={Boolean(p("payments.hold_on_unverified_vendor", true))} onChange={(v) => setP("payments.hold_on_unverified_vendor", v)} /></Field>
        <Field label="Hold on bank change"><Toggle value={Boolean(p("payments.hold_on_bank_change", true))} onChange={(v) => setP("payments.hold_on_bank_change", v)} /></Field>
        <Field label="Early-payment discounts"><Toggle value={Boolean(p("payments.early_payment_discounts_enabled", true))} onChange={(v) => setP("payments.early_payment_discounts_enabled", v)} /></Field>
      </Section>
      )}


      {activeSection === "ai" && ( <Section title="AI & Document Intelligence" description="AI processing, confidence thresholds, OCR, embeddings and Copilot.">
        <Field label="AI enabled"><Toggle value={draft.settings.ai_enabled} onChange={(v) => { updateSetting("ai_enabled", v); setP("ai.enabled", v); }} /></Field>
        <Field label="Automatic analysis"><Toggle value={draft.settings.auto_analyze} onChange={(v) => { updateSetting("auto_analyze", v); setP("ai.auto_analysis", v); }} /></Field>
        <Field label="Document intelligence"><Toggle value={Boolean(p("ai.document_intelligence", true))} onChange={(v) => setP("ai.document_intelligence", v)} /></Field>
        <Field label="AI model"><Input value={draft.settings.ai_model_preference} onChange={(v) => updateSetting("ai_model_preference", v)} /></Field>
        <Field label="AI temperature"><Input type="number" value={draft.settings.ai_temperature} onChange={(v) => updateSetting("ai_temperature", Number(v))} min={0} max={2} step={0.1} /></Field>
        <Field label="Embeddings"><Toggle value={draft.settings.enable_embeddings} onChange={(v) => updateSetting("enable_embeddings", v)} /></Field>
        <Field label="Copilot"><Toggle value={draft.settings.copilot_enabled} onChange={(v) => updateSetting("copilot_enabled", v)} /></Field>
        <Field label="Copilot memory days"><Input type="number" value={draft.settings.copilot_memory_days} onChange={(v) => updateSetting("copilot_memory_days", Number(v))} min={0} /></Field>
        <Field label="Copilot context documents"><Input type="number" value={draft.settings.copilot_max_context_docs} onChange={(v) => updateSetting("copilot_max_context_docs", Number(v))} min={1} /></Field>
        <Field label="High confidence threshold %"><Input type="number" value={Number(p("ai.high_confidence_threshold", 90))} onChange={(v) => setP("ai.high_confidence_threshold", Number(v))} min={0} max={100} /></Field>
        <Field label="Medium confidence threshold %"><Input type="number" value={Number(p("ai.medium_confidence_threshold", 75))} onChange={(v) => setP("ai.medium_confidence_threshold", Number(v))} min={0} max={100} /></Field>
        <Field label="Critical fields require confidence"><Toggle value={Boolean(p("ai.critical_fields_require_confidence", true))} onChange={(v) => setP("ai.critical_fields_require_confidence", v)} /></Field>
        <Field label="Critical fields"><Input value={String((p("ai.critical_fields", []) as string[]).join(", "))} onChange={(v) => setP("ai.critical_fields", v.split(",").map((x) => x.trim()).filter(Boolean))} /></Field>
      </Section>
      )}


      {activeSection === "notifications" && ( <Section title="Notifications & Webhooks" description="Approval reminders, exceptions, payment alerts and outbound events.">
        <Field label="Email notifications"><Toggle value={draft.settings.email_notifications} onChange={(v) => updateSetting("email_notifications", v)} /></Field>
        <Field label="Notification email"><Input value={draft.settings.notification_email || ""} onChange={(v) => updateSetting("notification_email", v || null)} /></Field>
        <Field label="Approval requests"><Toggle value={Boolean(p("notifications.approval_requests", true))} onChange={(v) => setP("notifications.approval_requests", v)} /></Field>
        <Field label="Overdue approvals"><Toggle value={Boolean(p("notifications.approval_overdue", true))} onChange={(v) => setP("notifications.approval_overdue", v)} /></Field>
        <Field label="Exception alerts"><Toggle value={Boolean(p("notifications.exceptions", true))} onChange={(v) => setP("notifications.exceptions", v)} /></Field>
        <Field label="Payment ready alerts"><Toggle value={Boolean(p("notifications.payment_ready", true))} onChange={(v) => setP("notifications.payment_ready", v)} /></Field>
        <Field label="Payment failure alerts"><Toggle value={Boolean(p("notifications.payment_failed", true))} onChange={(v) => setP("notifications.payment_failed", v)} /></Field>
        <Field label="Fraud alerts"><Toggle value={Boolean(p("notifications.fraud_alerts", true))} onChange={(v) => setP("notifications.fraud_alerts", v)} /></Field>
        <Field label="Duplicate alerts"><Toggle value={Boolean(p("notifications.duplicate_alerts", true))} onChange={(v) => setP("notifications.duplicate_alerts", v)} /></Field>
        <Field label="Slack webhook"><Input value={draft.settings.slack_webhook_url || ""} onChange={(v) => updateSetting("slack_webhook_url", v || null)} /></Field>
        <Field label="Outbound webhook"><Input value={draft.settings.outbound_webhook_url || ""} onChange={(v) => updateSetting("outbound_webhook_url", v || null)} /></Field>
        <Field label="Webhook enabled"><Toggle value={Boolean(p("webhooks.enabled", false))} onChange={(v) => setP("webhooks.enabled", v)} /></Field>
        <Field label="Approval reminder hours"><Input type="number" value={Number(p("notifications.approval_reminder_hours", 24))} onChange={(v) => setP("notifications.approval_reminder_hours", Number(v))} min={1} /></Field>
      </Section>
      )}


      {activeSection === "integrations" && ( <Section title="Integrations & Export Policy" description="ERP synchronization policy and export gates. Connection credentials remain in their dedicated integration flows.">
        <Field label="Invoice sync"><Toggle value={Boolean(p("integrations.invoice_sync", true))} onChange={(v) => setP("integrations.invoice_sync", v)} /></Field>
        <Field label="Vendor sync"><Toggle value={Boolean(p("integrations.vendor_sync", true))} onChange={(v) => setP("integrations.vendor_sync", v)} /></Field>
        <Field label="Chart of accounts sync"><Toggle value={Boolean(p("integrations.chart_of_accounts_sync", true))} onChange={(v) => setP("integrations.chart_of_accounts_sync", v)} /></Field>
        <Field label="Payment status sync"><Toggle value={Boolean(p("integrations.payment_status_sync", true))} onChange={(v) => setP("integrations.payment_status_sync", v)} /></Field>
        <Field label="PO sync"><Toggle value={Boolean(p("integrations.po_sync", true))} onChange={(v) => setP("integrations.po_sync", v)} /></Field>
        <Field label="Receipt sync"><Toggle value={Boolean(p("integrations.receipt_sync", true))} onChange={(v) => setP("integrations.receipt_sync", v)} /></Field>
        <Field label="Sync frequency"><Select value={String(p("integrations.sync_frequency", "automatic"))} onChange={(v) => setP("integrations.sync_frequency", v)} options={["automatic", "hourly", "daily", "manual"].map((v) => ({ value: v, label: v }))} /></Field>
        <Field label="Maximum retries"><Input type="number" value={Number(p("integrations.max_retries", 3))} onChange={(v) => setP("integrations.max_retries", Number(v))} min={0} /></Field>
        <Field label="Export only after approval"><Toggle value={Boolean(p("integrations.export_only_after_approval", true))} onChange={(v) => setP("integrations.export_only_after_approval", v)} /></Field>
        <LinkCard title="Accounting integrations" description="Manage QuickBooks/Xero connection flows already present in InvoiAI." href="/dashboard/billing" />
      </Section>
      )}


      {activeSection === "security" && ( <Section title="Security, Roles & Segregation of Duties" description="Organization access, approval authority, delegation and security controls.">
        <Field label="MFA required"><Toggle value={Boolean(p("security.mfa_required", false))} onChange={(v) => setP("security.mfa_required", v)} /></Field>
        <Field label="Session timeout minutes"><Input type="number" value={Number(p("security.session_timeout_minutes", 480))} onChange={(v) => setP("security.session_timeout_minutes", Number(v))} min={15} /></Field>
        <Field label="Sensitive-action re-authentication"><Toggle value={Boolean(p("security.sensitive_action_reauth", true))} onChange={(v) => setP("security.sensitive_action_reauth", v)} /></Field>
        <Field label="Payment release re-authentication"><Toggle value={Boolean(p("security.payment_release_reauth", true))} onChange={(v) => setP("security.payment_release_reauth", v)} /></Field>
        <Field label="Bank-change re-authentication"><Toggle value={Boolean(p("security.bank_change_reauth", true))} onChange={(v) => setP("security.bank_change_reauth", v)} /></Field>
        <Field label="IP restrictions"><Toggle value={Boolean(p("security.ip_restrictions_enabled", false))} onChange={(v) => setP("security.ip_restrictions_enabled", v)} /></Field>
        <div style={{ marginTop: 18 }}><LinkCard title="Organization Access & Approval" description="Manage roles, approval limits, delegations and segregation-of-duties rules." href="/dashboard/settings/organization-access" /><LinkCard title="AP Approval Rules" description="Configure rule-based approval routing and approval groups." href="/dashboard/settings/ap-rules" /><LinkCard title="Chart of Accounts" description="Manage the accounts invoice lines can be coded to. AP coding cannot run without them." href="/dashboard/settings/accounting" /></div>
      </Section>
      )}


      {activeSection === "audit" && ( <Section title="Audit, Retention & Analytics" description="Auditability, data retention and analytics controls.">
        <Field label="Audit logging"><Toggle value={Boolean(p("audit.enabled", true))} onChange={(v) => setP("audit.enabled", v)} /></Field>
        <Field label="Log settings changes"><Toggle value={Boolean(p("audit.log_settings_changes", true))} onChange={(v) => setP("audit.log_settings_changes", v)} /></Field>
        <Field label="Log payment changes"><Toggle value={Boolean(p("audit.log_payment_changes", true))} onChange={(v) => setP("audit.log_payment_changes", v)} /></Field>
        <Field label="Log bank changes"><Toggle value={Boolean(p("audit.log_bank_changes", true))} onChange={(v) => setP("audit.log_bank_changes", v)} /></Field>
        <Field label="Analytics enabled"><Toggle value={draft.settings.analytics_enabled} onChange={(v) => updateSetting("analytics_enabled", v)} /></Field>
        <Field label="Analytics retention months"><Input type="number" value={draft.settings.analytics_retention_months} onChange={(v) => updateSetting("analytics_retention_months", Number(v))} min={1} /></Field>
        <Field label="Document retention months"><Input type="number" value={Number(p("retention.document_retention_months", 84))} onChange={(v) => setP("retention.document_retention_months", Number(v))} min={1} /></Field>
        <Field label="AI data retention months"><Input type="number" value={Number(p("retention.ai_data_retention_months", 24))} onChange={(v) => setP("retention.ai_data_retention_months", Number(v))} min={1} /></Field>
        <Field label="Audit log retention months"><Input type="number" value={Number(p("retention.audit_log_retention_months", 84))} onChange={(v) => setP("retention.audit_log_retention_months", Number(v))} min={1} /></Field>
        <Field label="Deleted-document retention days"><Input type="number" value={Number(p("retention.deleted_document_retention_days", 30))} onChange={(v) => setP("retention.deleted_document_retention_days", Number(v))} min={0} /></Field>
      </Section>
      )}


      {activeSection === "branding" && ( <Section title="Branding & Vendor Experience" description="Email, vendor portal and organization presentation settings.">
        <Field label="Brand color"><Input value={draft.settings.brand_color || ""} onChange={(v) => updateSetting("brand_color", v || null)} /></Field>
        <Field label="Custom domain"><Input value={draft.settings.custom_domain || ""} onChange={(v) => updateSetting("custom_domain", v || null)} /></Field>
        <Field label="Email branding"><Toggle value={Boolean(p("branding.email_branding", true))} onChange={(v) => setP("branding.email_branding", v)} /></Field>
        <Field label="Vendor portal branding"><Toggle value={Boolean(p("branding.vendor_portal_branding", true))} onChange={(v) => setP("branding.vendor_portal_branding", v)} /></Field>
        <Field label="Email sender name"><Input value={String(p("branding.email_sender_name", ""))} onChange={(v) => setP("branding.email_sender_name", v || null)} /></Field>
        <Field label="Email sender address"><Input value={String(p("branding.email_sender_address", ""))} onChange={(v) => setP("branding.email_sender_address", v || null)} /></Field>
      </Section>
      )}


      {activeSection === "enterprise" && ( <Section title="SSO & Enterprise Authentication" description="Configure enterprise identity settings. Provider secrets should be stored securely and are not displayed here.">
        <Field label="SSO provider"><Select value={draft.settings.sso_provider || ""} onChange={(v) => updateSetting("sso_provider", v || null)} options={[{ value: "", label: "Disabled" }, { value: "saml", label: "SAML 2.0" }, { value: "oidc", label: "OpenID Connect" }]} /></Field>
        <Field label="SSO configuration"><Input value={JSON.stringify(draft.settings.sso_config || {})} onChange={(v) => { try { updateSetting("sso_config", JSON.parse(v)); } catch { /* keep last valid JSON */ } }} /></Field>
      </Section>
      )}


      {activeSection === "account" && ( <Section title="Account, Billing & Integrations" description="Existing dedicated product areas remain the source of truth for account-level actions.">
        <div style={{ marginBottom: 12 }}><div className="settings-key">Signed-in account</div><div className="settings-sub">{user?.email || "—"} · {user?.plan?.toUpperCase() || "FREE"}</div></div>
        <LinkCard title="Billing & Plan" description="Manage plan, usage and billing." href="/dashboard/billing" />
        <LinkCard title="Google Sheets" description="Use the existing export/integration flow." href="/dashboard" />
      </Section>
      )}

      {activeSection === "account" && (
        <div className="settings-danger-card">
          <div>
            <div className="settings-danger-title">Danger zone</div>
            <div className="settings-sub">Sign out of your InvoiAI account on this device.</div>
          </div>
          <button className="settings-danger-button" onClick={() => logout()}>Sign out</button>
        </div>
      )}

      <div className="settings-footer-note"><ShieldCheck size={14} /> Settings changes are permission-controlled and audited.</div>
    </main>
  </div>
</div>


</DashboardLayout>;
}