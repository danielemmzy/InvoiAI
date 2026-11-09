"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check, Loader2, Sparkles } from "lucide-react";
import { onboardingApi, type OnboardingData } from "@/api/workspaces";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { useAppStore } from "@/store/useAppStore";
import type { CompanySize } from "@/types/workspace";
import styles from "./workspace.module.css";

const TOTAL_STEPS = 6;
const COUNTRIES = [
  ["GB", "United Kingdom"], ["US", "United States"], ["NG", "Nigeria"],
  ["IE", "Ireland"], ["CA", "Canada"], ["AU", "Australia"], ["GH", "Ghana"],
  ["KE", "Kenya"], ["ZA", "South Africa"], ["AE", "United Arab Emirates"], ["SA", "Saudi Arabia"], ["DE", "Germany"], ["FR", "France"], ["NL", "Netherlands"],
];
const CURRENCIES = ["GBP", "USD", "NGN", "EUR", "CAD", "AUD", "GHS", "KES", "ZAR", "AED", "SAR"];
const COUNTRY_CURRENCY: Record<string, string> = { GB: "GBP", US: "USD", NG: "NGN", IE: "EUR", DE: "EUR", FR: "EUR", NL: "EUR", CA: "CAD", AU: "AUD", GH: "GHS", KE: "KES", ZA: "ZAR", AE: "AED", SA: "SAR" };
const DEFAULT_DATA: OnboardingData = {
  name: "", country: "GB", currency: "GBP", business_type: "registered_company", industry: "consulting",
  company_size: "2-10", monthly_invoice_volume: "11-25", accounting_software: "not_sure", invite_emails: [], approver_email: "",
};
const SIZE_CHOICES: { value: CompanySize; label: string }[] = [
  { value: "1", label: "Just me" }, { value: "2-10", label: "2–10" }, { value: "11-50", label: "11–50" },
  { value: "51-200", label: "51–200" }, { value: "201-500", label: "201–500" }, { value: "500+", label: "500+" },
];
const TITLES = ["Your business", "Business details", "Your workload", "Accounting software", "Invite teammates", "Review setup"];

export default function WorkspacePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: workspaces, isLoading: workspacesLoading, isError } = useWorkspaces();
  const setActiveWorkspace = useAppStore((state) => state.setActiveWorkspace);
  const [data, setData] = useState<OnboardingData>(DEFAULT_DATA);
  const [step, setStep] = useState(1);
  const [loaded, setLoaded] = useState(false);
  const [draftLoadFailed, setDraftLoadFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [inviteText, setInviteText] = useState("");
  const saveQueue = useRef<Promise<unknown>>(Promise.resolve());

  const persistDraft = useCallback((targetStep: number, answers: OnboardingData) => {
    const operation = saveQueue.current.catch(() => undefined).then(() => onboardingApi.saveDraft(targetStep, answers));
    saveQueue.current = operation.catch(() => undefined);
    return operation;
  }, []);

  useEffect(() => {
    let active = true;
    onboardingApi.getDraft().then((draft) => {
      if (!active) return;
      const restored = { ...DEFAULT_DATA, ...draft.data } as OnboardingData;
      setData(restored);
      setStep(Math.min(TOTAL_STEPS, Math.max(1, draft.step || 1)));
      setInviteText((restored.invite_emails || []).join(", "));
      setLoaded(true);
    }).catch(() => {
      if (active) { setError("We couldn’t load your saved setup. Try again."); setDraftLoadFailed(true); }
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!loaded) return;
    const timer = window.setTimeout(() => {
      setSaving(true);
      persistDraft(step, data).catch(() => setError("Your latest changes could not be saved. Check your connection and try again."))
        .finally(() => setSaving(false));
    }, 500);
    return () => window.clearTimeout(timer);
  }, [data, step, loaded, persistDraft]);

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("create");
    if (!workspacesLoading && workspaces?.length && !requested) window.location.replace("/dashboard");
  }, [workspacesLoading, workspaces]);

  function update<K extends keyof OnboardingData>(key: K, value: OnboardingData[K]) {
    setData((current) => ({ ...current, [key]: value }));
    setError("");
  }

  function validStep() {
    if (step === 1 && (data.name.trim().length < 2 || !data.country || !data.currency)) return "Enter your business name, country, and currency.";
    if (step === 2 && (!data.business_type || !data.industry)) return "Choose a business type and industry.";
    if (step === 5) {
      const emailPattern = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
      if (data.invite_emails.length > 10 || data.invite_emails.some((email) => !emailPattern.test(email))) return "Check teammate email addresses (up to 10).";
      if (data.approver_email && !emailPattern.test(data.approver_email)) return "Enter a valid approver email address.";
    }
    return "";
  }

  async function next() {
    const message = validStep();
    if (message) { setError(message); return; }
    const nextStep = Math.min(TOTAL_STEPS, step + 1);
    setSaving(true);
    try { await persistDraft(nextStep, data); setStep(nextStep); setError(""); }
    catch { setError("We couldn’t save this step. Please try again."); }
    finally { setSaving(false); }
  }

  async function finish() {
    const message = validStep();
    if (message) { setError(message); setStep(1); return; }
    setSubmitting(true); setError("");
    try {
      await persistDraft(TOTAL_STEPS, data);
      const workspace = await onboardingApi.complete(data);
      queryClient.clear();
      setActiveWorkspace(workspace);
      router.replace("/dashboard");
    } catch {
      setError("Workspace setup couldn’t be completed. Your answers are saved; try again.");
      setSubmitting(false);
    }
  }

  if (loading || workspacesLoading) return <main className={styles.page}><div className={styles.loading}><Loader2 className={styles.spin} /> Preparing your setup…</div></main>;
  if (draftLoadFailed) return <main className={styles.page}><div className={styles.card}><h1>We couldn’t load your saved setup.</h1><p>Your answers are still on your account. Refresh and try again.</p><button className={styles.primary} onClick={() => window.location.reload()}>Try again</button></div></main>;
  if (isError) return <main className={styles.page}><div className={styles.card}><h1>We couldn’t load your workspace.</h1><p>Your saved setup is safe. Refresh and try again.</p><button className={styles.primary} onClick={() => window.location.reload()}>Try again</button></div></main>;

  const select = (value: string, options: [string, string][], onChange: (value: string) => void) => (
    <select className={styles.select} value={value} onChange={(event) => onChange(event.target.value)}>
      {options.map(([option, label]) => <option key={option} value={option}>{label}</option>)}
    </select>
  );

  return <main className={styles.page}>
    <header className={styles.header}><div className={styles.brand}><span><Sparkles size={16} /></span> InvoiAI</div><div className={styles.saved}>{saving ? "Saving…" : "Your progress saves automatically"}</div></header>
    <section className={styles.card}>
      <div className={styles.progressLabel}>STEP {step} OF {TOTAL_STEPS}<span>{Math.round(step / TOTAL_STEPS * 100)}%</span></div>
      <div className={styles.progress} role="progressbar" aria-label="Onboarding progress" aria-valuemin={0} aria-valuemax={TOTAL_STEPS} aria-valuenow={step}><i style={{ width: `${step / TOTAL_STEPS * 100}%` }} /></div>
      <p className={styles.eyebrow}>BUSINESS WORKSPACE SETUP</p>
      <h1>{TITLES[step - 1]}</h1>
      <p className={styles.intro}>A few details help us shape your accounts payable workspace. You can change these later.</p>

      {step === 1 && <div className={styles.fields}>
        <label>Business or workspace name<input autoFocus value={data.name} maxLength={120} onChange={(e) => update("name", e.target.value)} placeholder="e.g. Northstar Consulting" /></label>
        <div className={styles.row}><label>Country{select(data.country, COUNTRIES as [string, string][], (country) => setData((current) => ({ ...current, country, currency: COUNTRY_CURRENCY[country] || current.currency })))}</label>
          <label>Default currency{select(data.currency, CURRENCIES.map((currency) => [currency, currency] as [string, string]), (currency) => update("currency", currency))}</label></div>
        <p className={styles.hint}>Your country suggests a default currency. You can choose another; invoices keep their original currency.</p>
      </div>}

      {step === 2 && <div className={styles.fields}>
        <label>Business registration status{select(data.business_type, [["registered_company", "Registered company"], ["sole_trader", "Sole trader"], ["partnership", "Partnership"], ["not_registered", "Not registered yet"]], (v) => update("business_type", v as OnboardingData["business_type"]))}</label>
        <label>Industry{select(data.industry, [["consulting", "Consulting"], ["professional_services", "Professional services"], ["agency", "Agency"], ["technology", "Technology"], ["construction", "Construction"], ["healthcare", "Healthcare"], ["other", "Other"]], (v) => update("industry", v))}</label>
        <p className={styles.hint}>We don’t need a company registration number or tax ID.</p>
      </div>}

      {step === 3 && <div className={styles.fields}>
        <label>How many people are on your team?{select(data.company_size, SIZE_CHOICES.map((x) => [x.value, x.label] as [string, string]), (v) => update("company_size", v as CompanySize))}</label>
        <label>About how many supplier invoices do you process each month?{select(data.monthly_invoice_volume, [["1-10", "1–10"], ["11-25", "11–25"], ["26-100", "26–100"], ["101-500", "101–500"], ["500+", "More than 500"]], (v) => update("monthly_invoice_volume", v as OnboardingData["monthly_invoice_volume"]))}</label>
      </div>}

      {step === 4 && <div className={styles.fields}>
        <label>Which accounting software do you use?{select(data.accounting_software, [["xero", "Xero"], ["quickbooks", "QuickBooks Online"], ["sage", "Sage Accounting"], ["none", "No accounting software"], ["not_sure", "Not sure yet"]], (v) => update("accounting_software", v as OnboardingData["accounting_software"]))}</label>
        {(data.accounting_software === "none" || data.accounting_software === "not_sure") && <div className={styles.note}>That’s fine. You can use manual accounts payable and connect software later.</div>}
        {data.accounting_software === "sage" && <div className={styles.note}>We’ll verify your Sage product and edition during connection setup before enabling sync.</div>}
      </div>}

      {step === 5 && <div className={styles.fields}>
        <label>Invite teammates <span className={styles.optional}>Optional</span><textarea rows={3} value={inviteText} onChange={(e) => { setInviteText(e.target.value); update("invite_emails", e.target.value.split(/[\s,;]+/).map((x) => x.trim()).filter(Boolean).slice(0, 10)); }} placeholder="Add email addresses separated by commas" /></label>
        <label>Who should approve invoices? <span className={styles.optional}>Optional</span><input type="email" value={data.approver_email} onChange={(e) => update("approver_email", e.target.value)} placeholder="approver@company.com" /></label>
        <div className={styles.note}>Preview only: {1 + new Set([...data.invite_emails, ...(data.approver_email ? [data.approver_email] : [])]).size} seats would be used, including you. No invitations are sent during setup; you can invite people later.</div>
      </div>}

      {step === 6 && <div className={styles.summary}>
        <div><span>Workspace</span><strong>{data.name || "Business name"}</strong></div>
        <div><span>Country and currency</span><strong>{data.country} · {data.currency}</strong></div>
        <div><span>Business</span><strong>{data.business_type.replaceAll("_", " ")} · {data.industry.replaceAll("_", " ")}</strong></div>
        <div><span>Team and volume</span><strong>{data.company_size} people · {data.monthly_invoice_volume} invoices/month</strong></div>
        <div><span>Accounting software</span><strong>{data.accounting_software === "none" ? "Manual workflow" : data.accounting_software.replaceAll("_", " ")}</strong></div>
        <div><span>Invite preview</span><strong>{data.invite_emails.length} teammate(s) · {data.approver_email || "No approver assigned"}</strong></div>
        <p className={styles.hint}>No tax ID, company registration number, payment card, or referral code is needed.</p>
      </div>}

      {error && <div role="alert" className={styles.error}>{error}</div>}
      <footer className={styles.actions}>
        {step > 1 ? <button className={styles.back} onClick={() => setStep((current) => current - 1)} disabled={submitting}><ArrowLeft size={16} /> Back</button> : <span />}
        {step < TOTAL_STEPS ? <button className={styles.primary} onClick={next} disabled={saving || submitting}>{saving ? <Loader2 className={styles.spin} /> : null} Continue <ArrowRight size={16} /></button>
          : <button className={styles.primary} onClick={finish} disabled={submitting || saving}>{submitting ? <Loader2 className={styles.spin} /> : <Check size={17} />} Create workspace</button>}
      </footer>
    </section>
  </main>;
}
