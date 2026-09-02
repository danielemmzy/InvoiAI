"use client";
// ============================================================
// SECURITY FIX (see SECURITY_FIXES_APPLIED.md item #2): the recovery
// access_token that Supabase puts in this page's URL fragment used to
// get written to localStorage and a JS-readable cookie so later
// requests could pick it up. It now stays in React state only, and is
// attached as an explicit Authorization header on the one
// /auth/reset-password call that needs it (see api/auth.ts). Nothing
// about this token ever touches storage.
// ============================================================
import Link from "next/link";
import { useEffect, useState } from "react";
import { KeyRound, Loader2, CheckCircle2 } from "lucide-react";
import { authApi } from "@/api/auth";
import { getErrorMessage } from "@/api/client";

export default function ResetPasswordPage() {
  const [recoveryToken, setRecoveryToken] = useState<string | null>(null);
  const [tokenMissing, setTokenMissing] = useState(false);

  useEffect(() => {
    const hash = window.location.hash.replace(/^#/, "");
    const params = new URLSearchParams(hash);
    const access = params.get("access_token");
    if (access) {
      setRecoveryToken(access);
      window.history.replaceState({}, document.title, window.location.pathname);
    } else {
      setTokenMissing(true);
    }
  }, []);

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (!recoveryToken) {
      setError("This reset link is invalid or expired. Request a new one.");
      return;
    }
    setBusy(true);
    try {
      await authApi.resetPassword(password, recoveryToken);
      setDone(true);
    } catch (e) {
      setError(getErrorMessage(e, "This reset link is invalid or expired. Request a new one."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-art">
        <div className="auth-panel-brand">Invoi<span>AI</span></div>
        <div className="ledger">
          <KeyRound size={21} color="#B98532" />
          <h2 style={{ fontFamily: "var(--display)", fontSize: 30, margin: "16px 0 8px" }}>Choose a new key.</h2>
          <p style={{ color: "#aaa", lineHeight: 1.7, fontSize: 14 }}>Use a strong password you don&apos;t reuse elsewhere.</p>
        </div>
      </div>
      <main className="auth-form-wrap">
        <section className="auth-form">
          <h1 className="auth-title">{done ? "Password updated" : "Create a new password"}</h1>
          {done ? (
            <>
              <div className="soft-notice">
                <CheckCircle2 size={18} />
                <div>Your password has been changed successfully.</div>
              </div>
              <Link href="/login" className="auth-submit" style={{ marginTop: 20, textDecoration: "none" }}>
                Continue to sign in
              </Link>
            </>
          ) : (
            <>
              <p className="auth-subtitle">Choose at least 8 characters. The reset link must still be valid.</p>
              {tokenMissing && (
                <div className="form-error">
                  This link is missing its reset token. Open it directly from the email instead of a bookmark or forward.
                </div>
              )}
              <form onSubmit={submit}>
                <div className="auth-field">
                  <label htmlFor="password">New password</label>
                  <input id="password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </div>
                <div className="auth-field">
                  <label htmlFor="confirm">Confirm password</label>
                  <input id="confirm" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
                </div>
                {error && <div className="form-error">{error}</div>}
                <button className="auth-submit" disabled={busy}>
                  {busy ? <><Loader2 size={16} className="animate-spin" />Updating…</> : "Update password"}
                </button>
              </form>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
