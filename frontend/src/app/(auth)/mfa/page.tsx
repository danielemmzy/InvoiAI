"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Check, Copy, KeyRound, Loader2, ShieldCheck, Trash2 } from "lucide-react";
import { authApi, type MfaFactor } from "@/api/auth";
import { getErrorMessage } from "@/api/client";
import { useAppStore } from "@/store/useAppStore";
import { workspacesApi } from "@/api/workspaces";
import { mfaQrImageSource } from "@/lib/mfa-qr";

type Enrollment = {
  factor_id: string;
  friendly_name: string;
  qr_code: string | null;
  secret: string | null;
  uri: string | null;
};

export default function MfaPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [factors, setFactors] = useState<MfaFactor[]>([]);
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [factorId, setFactorId] = useState("");
  const [code, setCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [stepUpFresh, setStepUpFresh] = useState(false);
  const [recoveryAccess, setRecoveryAccess] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const verifiedFactors = factors.filter((factor) => factor.status === "verified" && factor.type === "totp");
  const pendingFactors = factors.filter((factor) => factor.status === "unverified");
  const needsEnrollment = searchParams.get("mode") === "enroll" || verifiedFactors.length === 0;

  const loadFactors = useCallback(async () => {
    const result = await authApi.mfaFactors();
    setFactors(result.factors);
    setStepUpFresh(result.step_up_fresh);
    setFactorId((current) => current || result.factors.find((factor) => factor.status === "verified")?.id || "");
  }, []);

  useEffect(() => {
    let active = true;
    authApi.mfaFactors()
      .then((result) => {
        if (!active) return;
        setFactors(result.factors);
        setStepUpFresh(result.step_up_fresh);
        setFactorId(result.factors.find((factor) => factor.status === "verified")?.id || "");
      })
      .catch((reason: unknown) => {
        if (active) setError(getErrorMessage(reason, "Could not load authenticator settings."));
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function startEnrollment() {
    setBusy(true);
    setError("");
    try {
      setEnrollment(await authApi.mfaEnroll("InvoiAI authenticator"));
    } catch (reason) {
      setError(getErrorMessage(reason, "Could not start authenticator setup."));
    } finally {
      setBusy(false);
    }
  }

  async function startChallenge() {
    if (!factorId) return;
    setBusy(true);
    setError("");
    try {
      const result = await authApi.mfaChallenge(factorId);
      setChallengeId(result.challenge_id);
    } catch (reason) {
      setError(getErrorMessage(reason, "Could not start the verification challenge."));
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const currentFactorId = enrollment?.factor_id || factorId;
    if (!challengeId || !currentFactorId) return;
    setBusy(true);
    setError("");
    try {
      const result = await authApi.mfaVerify(currentFactorId, challengeId, code);
      setChallengeId(null);
      setCode("");
      setEnrollment(null);
      setStepUpFresh(true);
      if (result.recovery_codes?.length) {
        setRecoveryCodes(result.recovery_codes);
      } else {
        await loadFactors();
      }
    } catch (reason) {
      setError(getErrorMessage(reason, "That authenticator code was not accepted."));
    } finally {
      setBusy(false);
    }
  }

  async function useRecoveryCode(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await authApi.mfaRecovery(recoveryCode);
      setRecoveryAccess(true);
      setRecoveryCode("");
    } catch (reason) {
      setError(getErrorMessage(reason, "That recovery code is invalid or has already been used."));
    } finally {
      setBusy(false);
    }
  }

  async function regenerateCodes() {
    setBusy(true);
    setError("");
    try {
      const result = await authApi.mfaRegenerateRecoveryCodes();
      setRecoveryCodes(result.recovery_codes);
    } catch (reason) {
      setError(getErrorMessage(reason, "Could not replace your recovery codes."));
    } finally {
      setBusy(false);
    }
  }

  async function removeFactor(id: string) {
    const factor = factors.find((item) => item.id === id);
    if (!factor) return;
    if (!window.confirm(`Remove ${factor.friendly_name || "this authenticator"}?`)) return;
    setBusy(true);
    setError("");
    try {
      await authApi.mfaRemoveFactor(id);
      setEnrollment(null);
      setChallengeId(null);
      await loadFactors();
    } catch (reason) {
      setError(getErrorMessage(reason, "Could not remove this authenticator."));
    } finally {
      setBusy(false);
    }
  }

  async function continueToWorkspace() {
    setBusy(true);
    setError("");
    try {
      const profile = await authApi.getMe();
      useAppStore.getState().setAuth(profile);
      const workspaces = await workspacesApi.list();
      const savedId = localStorage.getItem("active_workspace_id");
      const selected = workspaces.find((workspace) => workspace.id === savedId) || workspaces[0];
      useAppStore.getState().setActiveWorkspace(selected || null);

      const mfaReturn = sessionStorage.getItem("invoiai:mfa-return-to");
      sessionStorage.removeItem("invoiai:mfa-return-to");
      const next = mfaReturn && mfaReturn.startsWith("/") && !mfaReturn.startsWith("//") && !mfaReturn.startsWith("/mfa")
        ? mfaReturn
        : selected ? "/dashboard" : "/workspace";
      router.replace(next);
    } catch (reason) {
      setError(getErrorMessage(reason, "Authenticator verified, but we could not load your workspace."));
    } finally {
      setBusy(false);
    }
  }

  async function copyRecoveryCodes() {
    if (!recoveryCodes) return;
    try {
      await navigator.clipboard.writeText(recoveryCodes.join("\n"));
    } catch {
      setError("Copy was unavailable. Select and copy the codes below.");
    }
  }

  const beginChallengeForSelectedFactor = verifiedFactors.length > 0 && !challengeId && !enrollment;

  return (
    <div className="auth-shell">
      <aside className="auth-panel-brand" style={{ display: "grid", alignContent: "space-between", padding: 36, borderRadius: 24, background: "var(--ia-ink)" }}>
        <div>Invoi<span>AI</span></div>
        <div>
          <ShieldCheck size={34} aria-hidden="true" />
          <p style={{ maxWidth: 340, fontSize: 22, lineHeight: 1.25 }}>A second check before sensitive workspace changes.</p>
        </div>
        <p style={{ color: "#D9E2FF", fontSize: 13 }}>Authenticator setup is separate from email verification.</p>
      </aside>

      <main className="auth-form-wrap">
        <section className="auth-form" aria-labelledby="mfa-title">
          <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--ia-blue)", marginBottom: 18 }}>
            <KeyRound size={18} aria-hidden="true" />
            <span style={{ fontSize: 13, fontWeight: 700 }}>Account security</span>
          </div>
          <h1 id="mfa-title" className="auth-title">{needsEnrollment ? "Set up an authenticator" : "Verify it’s you"}</h1>
          <p className="auth-subtitle">{needsEnrollment ? "Use any authenticator app to protect your workspace administrator account." : "Enter the six-digit code from your authenticator app to continue."}</p>

          {loading ? <p role="status">Loading security settings…</p> : null}
          {error ? <p className="form-error" role="alert">{error}</p> : null}

          {recoveryCodes ? (
            <div className="soft-notice" role="status" style={{ display: "block" }}>
              <strong>Save these recovery codes now</strong>
              <p>Each code works once. This list will not be shown again, and any previous codes have been replaced.</p>
              <ol style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8, paddingLeft: 24 }}>
                {recoveryCodes.map((item) => <li key={item}><code>{item}</code></li>)}
              </ol>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button type="button" className="auth-submit" onClick={() => void copyRecoveryCodes()}><Copy size={15} aria-hidden="true" /> Copy codes</button>
                <button type="button" className="btn-secondary" onClick={() => { setRecoveryCodes(null); void continueToWorkspace(); }}>I saved them</button>
              </div>
            </div>
          ) : null}

          {!loading && !recoveryCodes && needsEnrollment && !enrollment ? (
            <>
              {pendingFactors.length > 0 ? (
                <div className="soft-notice" style={{ display: "block", marginBottom: 16 }}>
                  <strong>Setup was started earlier</strong>
                  <p>The QR secret is no longer available. Remove the pending setup to create a new one.</p>
                  {pendingFactors.map((factor) => <button key={factor.id} type="button" className="btn-secondary" disabled={busy} onClick={() => void removeFactor(factor.id)}><Trash2 size={14} aria-hidden="true" /> Remove pending setup</button>)}
                </div>
              ) : null}
              <button type="button" className="auth-submit" disabled={busy || pendingFactors.length > 0} onClick={() => void startEnrollment()}>
                {busy ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <KeyRound size={16} aria-hidden="true" />}
                Start setup
              </button>
            </>
          ) : null}

          {!loading && !recoveryCodes && enrollment ? (
            <div style={{ display: "grid", gap: 16 }}>
              <p>Scan this code with your authenticator app. You can also enter the setup key manually.</p>
              {enrollment.qr_code ? <img alt="Authenticator setup QR code" width={220} height={220} style={{ width: 220, maxWidth: "100%", height: "auto", border: "1px solid var(--ia-line)", borderRadius: 12, padding: 8, background: "white" }} src={mfaQrImageSource(enrollment.qr_code)} /> : null}
              <div className="auth-field"><label htmlFor="totp-secret">Setup key</label><input id="totp-secret" type="text" readOnly value={enrollment.secret || ""} autoComplete="off" /></div>
              <button type="button" className="btn-secondary" onClick={() => { setEnrollment(null); setError(""); }}>Cancel setup</button>
              <VerificationForm code={code} setCode={setCode} busy={busy} onSubmit={verifyCode} submitLabel="Verify authenticator" />
            </div>
          ) : null}

          {!loading && !recoveryCodes && !needsEnrollment && !enrollment ? (
            <div style={{ display: "grid", gap: 18 }}>
              <div>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>Your authenticators</div>
                {verifiedFactors.map((factor) => (
                  <div key={factor.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", padding: "12px 0", borderTop: "1px solid var(--ia-line)" }}>
                    <span>{factor.friendly_name || "Authenticator app"}</span>
                    <button type="button" className="btn-secondary" aria-label={`Remove ${factor.friendly_name || "authenticator"}`} disabled={busy || !stepUpFresh || verifiedFactors.length <= 1} onClick={() => void removeFactor(factor.id)}><Trash2 size={15} aria-hidden="true" /></button>
                  </div>
                ))}
                {pendingFactors.map((factor) => <div key={factor.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", padding: "12px 0", borderTop: "1px solid var(--ia-line)" }}><span>Pending setup · {factor.friendly_name || "Authenticator app"}</span><button type="button" className="btn-secondary" disabled={busy} onClick={() => void removeFactor(factor.id)}>Remove pending</button></div>)}
              </div>

              {beginChallengeForSelectedFactor ? (
                <div style={{ display: "grid", gap: 12 }}>
                  <button type="button" className="auth-submit" disabled={busy || !factorId} onClick={() => void startChallenge()}>
                    {busy ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <ShieldCheck size={16} aria-hidden="true" />}
                    Verify authenticator
                  </button>
                  {recoveryAccess ? <p role="status">Recovery access is active for five minutes. Add a replacement authenticator, then verify it.</p> : null}
                  <form onSubmit={useRecoveryCode}>
                    <div className="auth-field"><label htmlFor="recovery-code">Lost your authenticator? Use a recovery code</label><input id="recovery-code" type="text" autoComplete="one-time-code" value={recoveryCode} onChange={(event) => setRecoveryCode(event.target.value)} /></div>
                    <button type="submit" className="btn-secondary" disabled={busy || !recoveryCode.trim()}>Use recovery code</button>
                  </form>
                  {recoveryAccess ? <button type="button" className="btn-secondary" disabled={busy} onClick={() => void startEnrollment()}>Add replacement authenticator</button> : null}
                </div>
              ) : null}

              {challengeId ? <VerificationForm code={code} setCode={setCode} busy={busy} onSubmit={verifyCode} submitLabel="Continue" /> : null}
              {stepUpFresh ? <button type="button" className="btn-secondary" disabled={busy} onClick={() => void regenerateCodes()}><KeyRound size={15} aria-hidden="true" /> Replace recovery codes</button> : null}
              <p style={{ fontSize: 12, color: "var(--ia-muted)" }}>Sensitive organization changes require a recent authenticator check. That check expires after five minutes.</p>
            </div>
          ) : null}

          {!loading && !recoveryCodes && enrollment && !challengeId ? null : null}
          {!loading && !recoveryCodes && challengeId ? <p className="auth-subtitle" style={{ marginTop: 10 }}>Enter the current code. Pasting from your authenticator is supported.</p> : null}
          {!loading && !recoveryCodes && !needsEnrollment && !challengeId && stepUpFresh ? <button type="button" className="btn-secondary" style={{ marginTop: 12 }} onClick={() => void continueToWorkspace()}><Check size={15} aria-hidden="true" /> Continue to workspace</button> : null}
          {!loading && !recoveryCodes && !needsEnrollment && !challengeId && !stepUpFresh && verifiedFactors.length === 0 ? <button type="button" className="auth-submit" disabled={busy} onClick={() => void startEnrollment()}>Set up authenticator</button> : null}
        </section>
      </main>
    </div>
  );
}

function VerificationForm({
  code,
  setCode,
  busy,
  onSubmit,
  submitLabel,
}: {
  code: string;
  setCode: (value: string) => void;
  busy: boolean;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  submitLabel: string;
}) {
  return (
    <form onSubmit={onSubmit}>
      <div className="auth-field">
        <label htmlFor="authenticator-code">Six-digit authenticator code</label>
        <input
          id="authenticator-code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          value={code}
          onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
          required
          minLength={6}
          maxLength={6}
        />
      </div>
      <button type="submit" className="auth-submit" disabled={busy || code.length !== 6}>
        {busy ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <ShieldCheck size={16} aria-hidden="true" />}
        {submitLabel}
      </button>
    </form>
  );
}
