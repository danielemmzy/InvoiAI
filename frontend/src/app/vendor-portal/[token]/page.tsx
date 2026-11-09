"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { vendorPortalApi } from "@/api/ap";

export default function VendorPortalPage() {
  const { token } = useParams<{ token: string }>();
  const [requestType, setRequestType] = useState<"w9" | "bank_verification" | null>(null);
  const [vendorName, setVendorName] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [documentUrl, setDocumentUrl] = useState("");
  const [bank, setBank] = useState({
    account_holder_name: "",
    bank_name: "",
    account_number_last4: "",
    routing_number: "",
  });

  useEffect(() => {
    let active = true;
    vendorPortalApi.get(token).then((data) => {
      if (!active) return;
      setRequestType(data.request_type);
      setVendorName(data.vendor_name);
    }).catch((e) => {
      if (!active) return;
      setError(e instanceof Error ? e.message : "This link is invalid or expired.");
    });
    return () => { active = false; };
  }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      if (requestType === "w9") {
        if (!documentUrl.trim()) throw new Error("Please provide the W-9 document URL.");
        await vendorPortalApi.submitW9(token, documentUrl.trim());
      } else {
        await vendorPortalApi.submitBankVerification(token, bank);
      }
      setSubmitted(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submission failed.");
    }
  }

  if (submitted) {
    return <main style={{ maxWidth: 620, margin: "80px auto", padding: 24 }}>
      <h1>Submission received</h1>
      <p>Your information was submitted to the AP team. You can close this page.</p>
    </main>;
  }

  return <main style={{ maxWidth: 620, margin: "60px auto", padding: 24 }}>
    <h1>InvoiAI vendor portal</h1>
    {vendorName && <p>Request for <strong>{vendorName}</strong></p>}
    {error && <div role="alert" style={{ margin: "16px 0", color: "#b42318" }}>{error}</div>}
    {!requestType && !error ? <p>Loading request…</p> : null}
    {requestType && (
      <form onSubmit={submit} style={{ display: "grid", gap: 14 }}>
        {requestType === "w9" ? (
          <label>W-9 document URL
            <input value={documentUrl} onChange={(e) => setDocumentUrl(e.target.value)} required style={{ width: "100%" }} />
          </label>
        ) : (
          <>
            <label>Account holder name
              <input value={bank.account_holder_name} onChange={(e) => setBank({ ...bank, account_holder_name: e.target.value })} required />
            </label>
            <label>Bank name
              <input value={bank.bank_name} onChange={(e) => setBank({ ...bank, bank_name: e.target.value })} required />
            </label>
            <label>Account number (last 4)
              <input value={bank.account_number_last4} onChange={(e) => setBank({ ...bank, account_number_last4: e.target.value.slice(-4) })} inputMode="numeric" maxLength={4} required />
            </label>
            <label>Routing number
              <input value={bank.routing_number} onChange={(e) => setBank({ ...bank, routing_number: e.target.value })} required />
            </label>
          </>
        )}
        <button type="submit">Submit</button>
      </form>
    )}
  </main>;
}
