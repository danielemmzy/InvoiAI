"use client";
// Docs — /docs

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAppStore } from "@/store/useAppStore";
import MobileMenu from "@/components/marketing/MobileMenu";
import { Menu } from "lucide-react";

const SECTIONS = [
  { id: "getting-started", label: "Getting started" },
  { id: "connecting", label: "Connecting QuickBooks or Xero" },
  { id: "uploading", label: "Uploading documents" },
  { id: "health-score", label: "Understanding your Health Score" },
  { id: "approvals", label: "Approval workflows" },
  { id: "insights", label: "Insights & the daily scan" },
  { id: "copilot", label: "Using the Finance Copilot" },
  { id: "personal", label: "Personal finance mode" },
  { id: "faq", label: "FAQ" },
];

export default function DocsPage() {
  const { isAuthenticated } = useAppStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const [navScrolled, setNavScrolled] = useState(false);
  const [active, setActive] = useState(SECTIONS[0].id);

  useEffect(() => {
    function onScroll() {
      setNavScrolled(window.scrollY > 8);
      let current = SECTIONS[0].id;
      for (const s of SECTIONS) {
        const el = document.getElementById(s.id);
        if (el && el.getBoundingClientRect().top < 140) current = s.id;
      }
      setActive(current);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const closeMenu = () => setMenuOpen(false);

  return (
    <div style={{ background: "#F7F4EE", minHeight: "100vh" }}>
      {/* ── Navbar (desktop: inline links + CTA) ── */}
      <nav className="nav" style={navScrolled ? { boxShadow: "0 4px 24px rgba(26,25,22,0.05)" } : undefined}>
        <Link href="/" className="nav-logo serif" onClick={closeMenu}>
          Invoi<span>AI</span>
        </Link>
        <div className="nav-links">
          <Link href="/#product" className="nav-link">Product</Link>
          <Link href="/#pricing" className="nav-link">Pricing</Link>
          <Link href="/docs" className="nav-link" style={{ color: "#1A1916" }}>Docs</Link>
          {isAuthenticated ? (
            <Link href="/dashboard" className="nav-cta">Dashboard →</Link>
          ) : (
            <>
              <Link href="/login" className="nav-link">Sign in</Link>
              <Link href="/signup" className="nav-cta">Get started →</Link>
            </>
          )}
          <button
            className="nav-toggle"
            aria-label="Open menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={22} />
          </button>
        </div>
      </nav>

      {/* ── Mobile menu (full-screen takeover, not a shrunken desktop nav) ── */}
      <MobileMenu
        open={menuOpen}
        onClose={closeMenu}
        links={[
          { href: "/#product", label: "Product" },
          { href: "/#pricing", label: "Pricing" },
          { href: "/docs", label: "Docs" },
        ]}
        ctaHref="/signup"
        ctaLabel="Get started"
        secondaryHref={isAuthenticated ? "/dashboard" : "/login"}
        secondaryLabel={isAuthenticated ? "Go to dashboard" : "Sign in"}
      />

      {/* ── Docs hero ── */}
      <div className="docs-hero">
        <div className="section-label">Documentation</div>
        <h1 className="serif" style={{ fontSize: "clamp(32px,4vw,44px)", fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 14 }}>
          How to use InvoiAI
        </h1>
        <p style={{ fontSize: 15, color: "#6B6860", maxWidth: 560, lineHeight: 1.7 }}>
          Everything from connecting your accounting software to reading
          your first Health Score. If you get stuck, the Finance Copilot
          inside the dashboard can answer most of this too.
        </p>
      </div>

      {/* ── Docs layout ── */}
      <div className="docs-layout">
        <nav className="docs-nav" aria-label="Documentation sections">
          {SECTIONS.map((s) => (
            <a key={s.id} href={`#${s.id}`} className={`docs-nav-link${active === s.id ? " active" : ""}`}>
              {s.label}
            </a>
          ))}
        </nav>

        <div className="docs-content">
          <section id="getting-started">
            <h2>Getting started</h2>
            <p>
              Create a free account and choose a mode. Business mode is
              for teams running on QuickBooks or Xero; Personal mode
              is for individual budgeting. You can invite teammates
              later — mode doesn't lock you in.
            </p>
            <ol>
              <li><strong>Sign up</strong> — email and password, no card required.</li>
              <li><strong>Pick a mode</strong> — Business or Personal. This decides which Copilot tools and dashboard views you see.</li>
              <li><strong>Connect or upload</strong> — link QuickBooks/Xero for existing records, or start uploading documents right away.</li>
            </ol>
            <div className="docs-callout">
              You don't need an accounting platform connected to start.
              Manual upload works from day one — sync is additive, not required.
            </div>
          </section>

          <section id="connecting">
            <h2>Connecting QuickBooks or Xero</h2>
            <p>
              From <strong>Settings → Integrations</strong>, choose your platform
              and complete the OAuth flow. InvoiAI requests read/write
              access to vendors, customers, invoices, bills, payments,
              and purchase orders — nothing else.
            </p>
            <p>
              Once connected, a sync runs immediately, then on a rolling
              60-minute schedule. Changes made directly in QuickBooks or
              Xero (a new bill, a payment) also arrive in near-real-time
              through webhooks, so both systems stay current without you
              doing anything.
            </p>
            <div className="docs-code">POST /api/v1/integrations/quickbooks/connect{"\n"}POST /api/v1/integrations/xero/connect</div>
            <p>
              Disconnecting is one click and stops future syncs — it
              never deletes documents InvoiAI has already processed.
            </p>
          </section>

          <section id="uploading">
            <h2>Uploading documents</h2>
            <p>
              Drag in a PDF, JPG, PNG, or WEBP — up to 10MB. InvoiAI
              accepts invoices, receipts, bills, purchase orders, and
              bank statements. Digital PDFs are parsed directly; photos
              and scans go through GPT-4o Vision.
            </p>
            <ul>
              <li>Pick the closest industry for sharper field extraction — 12 are supported today.</li>
              <li>Exact duplicate files are rejected automatically by content hash.</li>
              <li>Processing is asynchronous — you'll see a status change from <em>processing</em> to <em>needs review</em> or <em>approved</em> within seconds.</li>
            </ul>
          </section>

          <section id="health-score">
            <h2>Understanding your Health Score</h2>
            <p>
              Every document is scored out of 100 by 8 checks running in
              parallel: OCR confidence, math consistency, vendor history,
              duplicate detection, historical anomaly, purchase order
              match, fraud signals, and compliance rules.
            </p>
            <ul>
              <li><strong>80–100 · Low risk</strong> — eligible for auto-approval if your policy allows it.</li>
              <li><strong>50–79 · Medium risk</strong> — routed for review by default.</li>
              <li><strong>20–49 · High risk</strong> — held for approval, flagged clearly.</li>
              <li><strong>0–19 · Critical</strong> — escalated automatically to an admin.</li>
            </ul>
            <p>
              Tap any score in the dashboard to see the per-module reasoning —
              InvoiAI explains exactly why a document scored the way it did,
              not just the number.
            </p>
          </section>

          <section id="approvals">
            <h2>Approval workflows</h2>
            <p>
              Set spending-limit thresholds in <strong>Settings → Approval policy</strong>.
              Documents above your limit — or flagged by the verification
              engine — route to the right approver automatically, with
              reminders after 24 hours and escalation to an admin if a
              step goes untouched past its deadline.
            </p>
            <p>
              Every decision is recorded in an immutable history —
              who approved what, when, and why — for audit purposes.
            </p>
          </section>

          <section id="insights">
            <h2>Insights & the daily scan</h2>
            <p>
              Once you're syncing real data, a daily analyzer pass looks
              for cash-runway risk, overdue receivables, vendor price
              increases, spending anomalies, and duplicate charges — pure
              computation, no AI guesswork. Findings appear as a ranked
              feed in your dashboard, critical items first.
            </p>
            <p>
              Click <strong>Generate follow-ups</strong> on an overdue-invoice
              insight and the Copilot drafts a reminder email for you to review and send.
            </p>
          </section>

          <section id="copilot">
            <h2>Using the Finance Copilot</h2>
            <p>
              The Copilot answers questions by calling the same analyzers
              that power your insight feed — it never queries your data
              directly or calculates numbers itself. That means every
              figure it gives you is traceable back to a real computation.
            </p>
            <p>Try asking things like:</p>
            <ul>
              <li>"Which vendor increased prices most this month?"</li>
              <li>"What's my cash runway right now?"</li>
              <li>"Draft a follow-up for my most overdue customer."</li>
            </ul>
          </section>

          <section id="personal">
            <h2>Personal finance mode</h2>
            <p>
              Switch to Personal mode and the same infrastructure serves
              you individually: log income and expenses in plain language,
              upload a bank statement for automatic categorization, and
              get a weekly allocation plan built from your real bills,
              debts, and goals — all deterministic, no LLM math involved.
            </p>
            <div className="docs-callout">
              Business and Personal mode share the same Copilot — just a
              different toolset. Nothing about your account is locked
              to one mode permanently.
            </div>
          </section>

          <section id="faq">
            <h2>FAQ</h2>
            <p><strong>Does InvoiAI replace QuickBooks or Xero?</strong> No — it sits on top of them. Your accounting platform stays the source of truth for your ledger; InvoiAI adds verification, sync, and insight on top.</p>
            <p><strong>What happens to a rejected document?</strong> It's marked rejected with the approver's comment attached, and never syncs to your accounting platform.</p>
            <p><strong>Can I export without connecting an integration?</strong> Yes — Excel and CSV export work on every plan with no integration required.</p>
            <p><strong>Is my data used to train models?</strong> No — your documents and financial data are used only to serve your account.</p>
          </section>
        </div>
      </div>

      {/* Footer */}
      <div style={{ borderTop: "0.5px solid #E2DDD4" }}>
        <div className="footer">
          <div className="footer-logo serif">Invoi<span>AI</span></div>
          <div className="footer-links">
            <Link href="/#product" className="footer-link">Product</Link>
            <Link href="/#pricing" className="footer-link">Pricing</Link>
            <Link href="/docs" className="footer-link">Docs</Link>
          </div>
          <div className="footer-text">© 2026 InvoiAI · Financial operations, watched daily.</div>
        </div>
      </div>
    </div>
  );
}
