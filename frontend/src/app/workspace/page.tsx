"use client";

import { useEffect, useMemo, useState } from "react";
import { Building2, Loader2, Plus, UserRound, ArrowRight, Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { useWorkspaces, useCreateWorkspace } from "@/hooks/useWorkspaces";
import type { CompanySize, WorkspaceType } from "@/types/workspace";

// Same bands the backend enforces (schemas/workspace.py CompanySize) —
// kept as a small closed set so this stays useful for segmentation
// later, not free text nobody can group on.
const COMPANY_SIZES: { value: CompanySize; label: string }[] = [
  { value: "1", label: "Just me" },
  { value: "2-10", label: "2–10" },
  { value: "11-50", label: "11–50" },
  { value: "51-200", label: "51–200" },
  { value: "201-500", label: "201–500" },
  { value: "500+", label: "500+" },
];

export default function WorkspacePage() {
  const router = useRouter();
  const { data: workspaces, isLoading, isError } = useWorkspaces();
  const create = useCreateWorkspace();
  const [type, setType] = useState<WorkspaceType | null>(null);
  const [businessName, setBusinessName] = useState("");
  const [companySize, setCompanySize] = useState<CompanySize | null>(null);
  const personalExists = useMemo(() => workspaces?.some((w) => w.type === "personal"), [workspaces]);

  useEffect(() => {
    const requested = typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("create")
      : null;

    // A request to create Personal must never strand the user on an empty
    // form when their Personal workspace already exists.
    if (requested === "personal" && personalExists) {
      router.replace("/dashboard");
      return;
    }

    if (requested === "personal" || requested === "business") {
      setType(requested);
    }
  }, [personalExists, router]);

  useEffect(() => {
    const requested = typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("create")
      : null;

    // Existing users with memberships go straight to their workspace.
    // An authenticated user with zero workspaces is NOT an error: this page
    // is the normal onboarding path for choosing Personal or Business.
    if (!isLoading && workspaces && workspaces.length > 0 && !requested) {
      router.replace("/dashboard");
    }
  }, [isLoading, workspaces, router]);

  if (isLoading) return <div className="workspace-onboarding"><div className="workspace-loading"><Loader2 className="animate-spin" size={20}/> Preparing your workspace…</div></div>;
  if (isError) return <div className="workspace-onboarding"><div className="workspace-card"><h1>We couldn’t load your workspaces</h1><p>Please refresh and try again. Your account is safe.</p><button className="btn-primary" onClick={() => location.reload()}>Try again</button></div></div>;

  return <div className="workspace-onboarding">
    <div className="workspace-brand">Invoi<span>AI</span></div>
    <div className="workspace-card">
      <div className="eyebrow">One account · multiple spaces</div>
      <h1>What are you here to manage?</h1>
      <p className="workspace-intro">Choose the workspace you want to create first. You can add the other type later and switch between them anytime.</p>
      <div className="workspace-options">
        <button className={`workspace-option ${type === "personal" ? "selected" : ""}`} disabled={personalExists} onClick={() => setType("personal")}>
          <span className="workspace-option-icon"><UserRound size={22}/></span>
          <span><strong>Personal</strong><small>Income, expenses, budgets, bills, debts and goals.</small></span>
          {personalExists ? <em>Already created</em> : <ArrowRight size={17}/>} 
        </button>
        <button className={`workspace-option ${type === "business" ? "selected" : ""}`} onClick={() => setType("business")}>
          <span className="workspace-option-icon"><Building2 size={22}/></span>
          <span><strong>Business</strong><small>Invoices, AP, vendors, approvals, GL coding and accounting integrations.</small></span>
          <ArrowRight size={17}/>
        </button>
      </div>
      {type === "business" && <div className="workspace-form">
        <label className="form-label">Business name</label>
        <input className="form-input" autoFocus value={businessName} onChange={(e) => setBusinessName(e.target.value)} placeholder="e.g. Acme Construction Ltd" maxLength={120}/>

        <label className="form-label" style={{ marginTop: 18 }}>How many people work there?</label>
        <div className="company-size-grid">
          {COMPANY_SIZES.map((s) => (
            <button
              type="button"
              key={s.value}
              className={`company-size-chip${companySize === s.value ? " selected" : ""}`}
              onClick={() => setCompanySize(s.value)}
            >
              {companySize === s.value && <Check size={12} />}
              {s.label}
            </button>
          ))}
        </div>
        <p className="workspace-note" style={{ marginTop: 8 }}>
          Helps us point you at the right plan — it&apos;s never a hard limit on your account.
        </p>
      </div>}
      <button
        className="form-submit workspace-create"
        disabled={!type || (type === "business" && (businessName.trim().length < 2 || !companySize)) || create.isPending}
        onClick={() => create.mutate({
          type: type!,
          name: type === "business" ? businessName.trim() : undefined,
          company_size: type === "business" ? companySize! : undefined,
        })}
      >
        {create.isPending ? <><Loader2 size={16} className="animate-spin"/> Creating workspace…</> : <><Plus size={16}/> Create {type === "personal" ? "personal" : "business"} workspace</>}
      </button>
      <p className="workspace-note">You can create additional business workspaces and switch between all of your workspaces from the dashboard.</p>
    </div>
  </div>;
}
