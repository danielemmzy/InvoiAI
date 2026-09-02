"use client";
// Landing page — /
// Hero + feature strip are the approved design and are left as they are.
// Everything below them is new: written from what the product actually does
// now, including GL coding, 2 & 3-way matching, workspaces, and the insight
// and copilot layers. Nav is the v3 pattern: inline desktop links plus a
// full-screen mobile takeover, not a shrunken copy of the desktop bar.

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode, type HTMLAttributes } from "react";
import { useAppStore } from "@/store/useAppStore";
import MobileMenu from "@/components/marketing/MobileMenu";
import {
  ArrowRight,
  Check,
  ShieldCheck,
  Mail,
  Menu,
  UploadCloud,
  Sparkles,
  UserCheck,
  RefreshCw,
  CheckCircle2,
  FileText,
  MessageSquare,
  ScanLine,
  Building2,
  User,
  TrendingUp,
  AlertTriangle,
  Wallet,
  Landmark,
  Sheet,
  GitCompareArrows,
  BookOpenCheck,
  KeyRound,
  History,
  Layers,
} from "lucide-react";

/* ────────────────────────────────────────────
   Scroll-reveal primitive
   ──────────────────────────────────────────── */
function useInView<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.unobserve(el);
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, inView };
}

function Reveal({
  children,
  delay = 0,
  className = "",
  ...rest
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
} & HTMLAttributes<HTMLDivElement>) {
  const { ref, inView } = useInView<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={`reveal ${inView ? "reveal-visible" : ""} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
      {...rest}
    >
      {children}
    </div>
  );
}

function StatCounter({
  value,
  prefix = "",
  suffix = "",
  label,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  label: string;
}) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!inView) return;
    let start: number | null = null;
    const duration = 1100;
    let raf: number;
    function step(ts: number) {
      if (start === null) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(eased * value));
      if (progress < 1) raf = requestAnimationFrame(step);
      else setCount(value);
    }
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [inView, value]);

  return (
    <div ref={ref} className="stat-item">
      <div className="stat-value serif">
        {prefix}
        {count}
        {suffix}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function HealthGauge({
  score,
  size = 84,
  stroke = 7,
  tone = "#1E7E4B",
  triggerKey,
}: {
  score: number;
  size?: number;
  stroke?: number;
  tone?: string;
  triggerKey?: string | number;
}) {
  const [filled, setFilled] = useState(false);
  useEffect(() => {
    setFilled(false);
    const t = setTimeout(() => setFilled(true), 80);
    return () => clearTimeout(t);
  }, [score, triggerKey]);

  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;

  return (
    <div className="health-gauge-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#E2DDD4" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={tone}
          strokeWidth={stroke}
          strokeLinecap="round"
          style={{
            strokeDasharray: circ,
            strokeDashoffset: filled ? offset : circ,
            transition: "stroke-dashoffset 1.1s cubic-bezier(.16,.84,.44,1)",
          }}
        />
      </svg>
      <div className="health-gauge-center">
        <div className="health-gauge-score serif" style={{ fontSize: size * 0.28 }}>{score}</div>
        <div className="health-gauge-max">/ 100</div>
      </div>
    </div>
  );
}

function Feature({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="feature-block">
      <div className="feature-icon">{icon}</div>
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────
   Data — mirrors the real intake → verify →
   match → code → approve → sync pipeline
   ──────────────────────────────────────────── */
const WORKFLOW_STEPS = [
  {
    n: "01",
    icon: UploadCloud,
    title: "An invoice arrives",
    desc: "Forward it to a controlled AP inbox or drop the file in yourself. Digital PDFs are read directly, photos and scans go through vision OCR first.",
  },
  {
    n: "02",
    icon: Sparkles,
    title: "AI reads it",
    desc: "The model pulls vendor, line items, dates and totals, tuned to your industry. Twelve industries are supported today, from construction to healthcare.",
  },
  {
    n: "03",
    icon: GitCompareArrows,
    title: "Matched to the evidence",
    desc: "Compared against the purchase order and, when one exists, the goods receipt. Quantities and unit prices have to line up within tolerance, not just the total.",
  },
  {
    n: "04",
    icon: BookOpenCheck,
    title: "Coded to your accounts",
    desc: "Checked against your coding rules first, then your own history with that vendor, and only then handed to a model to fill the gap. Every line carries a confidence score.",
  },
  {
    n: "05",
    icon: ShieldCheck,
    title: "Verified, eight ways",
    desc: "Math, OCR confidence, vendor history, duplicate detection, PO match, fraud signals and compliance rules all run in parallel and roll up into one Health Score.",
  },
  {
    n: "06",
    icon: UserCheck,
    title: "Routed, not rubber-stamped",
    desc: "Clean, low-risk invoices clear on their own. Anything above your threshold, or flagged by a check, goes to the right approver with reminders built in.",
  },
  {
    n: "07",
    icon: RefreshCw,
    title: "Synced and watched",
    desc: "Approved bills flow back to QuickBooks or Xero. From there, the insight engine keeps reading your books for whatever needs attention next.",
  },
];

const VERIFY_CHECKS = [
  { label: "OCR confidence" },
  { label: "Math check" },
  { label: "Vendor history" },
  { label: "Duplicate check" },
  { label: "Fraud signals" },
  { label: "Compliance rules" },
];

const INTEGRATIONS = [
  { icon: Landmark, name: "QuickBooks", desc: "Two-way sync for vendors, customers, invoices, bills, payments and purchase orders, on a schedule or in real time.", status: "Connected sync", live: true },
  { icon: Landmark, name: "Xero", desc: "The same normalized sync, built on the same domain model as QuickBooks, so switching platforms never means switching workflows.", status: "Connected sync", live: true },
  { icon: Sheet, name: "Google Sheets", desc: "Push any document's structured data straight into a live spreadsheet whenever you want a working copy outside InvoiAI.", status: "Export ready", live: true },
  { icon: Mail, name: "AP email inbox", desc: "Give vendors one address to send invoices to. Every attachment is verified against a signed sender check before it ever reaches your queue.", status: "Live intake", live: true },
];

const INSIGHTS_PREVIEW = [
  { icon: AlertTriangle, tone: "critical" as const, severity: "Critical", title: "$18,400 sitting across 7 overdue invoices", action: "Send payment reminders" },
  { icon: TrendingUp, tone: "warning" as const, severity: "Warning", title: "Acme Steel billed 14% above their usual rate", action: "Request a comparison quote" },
  { icon: Wallet, tone: "critical" as const, severity: "Critical", title: "Cash runway is down to 41 days", action: "Review upcoming payables" },
  { icon: ScanLine, tone: "warning" as const, severity: "Warning", title: "Software spend is up 26% this month", action: "Review new subscriptions" },
];

const INDUSTRIES = [
  "General", "Retail", "Construction", "Healthcare", "Hospitality", "Manufacturing",
  "Professional services", "Real estate", "Technology", "Transportation", "Education", "Nonprofit",
];

const CODING_ROWS = [
  { item: "Steel brackets, 40 units", account: "5200 · Materials", pct: 95, tone: "rule" as const, source: "Coding rule" },
  { item: "Freight and handling", account: "6100 · Shipping", pct: 88, tone: "history" as const, source: "Vendor history" },
  { item: "Site permit fee", account: "5450 · Permits & fees", pct: 62, tone: "ai" as const, source: "AI suggestion, needs a look" },
];

const EXCEPTIONS = [
  { vendor: "Halvorsen Fabrication", severity: "high" as const, reason: "Invoice total is $340 over the matched purchase order, past the 5% tolerance." },
  { vendor: "Bright Path Logistics", severity: "medium" as const, reason: "No goods receipt on file yet for PO-2291. Holding until receiving confirms." },
  { vendor: "Corvus Office Supply", severity: "medium" as const, reason: "Same invoice number seen 11 days ago from this vendor. Flagged as a possible duplicate." },
];

// Mirrors core/plan.py exactly. This page is pre-auth and doesn't call
// the backend, so these numbers are curated rather than fetched — the
// in-app billing page (/dashboard/billing) is the live-wired one, reading
// straight from GET /billing/plans. If a price or limit changes in
// core/plan.py, update it here too.
const PRICING_TIERS = [
  {
    plan: "Free", monthly: 0, annualMonthly: 0, featured: false, contactSales: false,
    features: ["15 documents / month", "1 QuickBooks or Xero connection", "2-way PO matching", "1 approval workflow", "CSV export", "1 seat"],
  },
  {
    plan: "Starter", monthly: 39, annualMonthly: 32, featured: true, contactSales: false,
    features: ["100 documents / month", "QuickBooks + Xero, both", "AI GL coding", "Insights feed & Finance Copilot", "Excel + Sheets export", "3 seats"],
  },
  {
    plan: "Pro", monthly: 119, annualMonthly: 109, featured: false, contactSales: false,
    features: ["Unlimited documents", "3-way matching + email intake", "Vendor analytics & cash flow", "Tolerance engine", "Audit trail", "10 seats"],
  },
  {
    plan: "Business", monthly: 349, annualMonthly: 279, featured: false, contactSales: false,
    features: ["Everything in Pro", "Unlimited seats", "Multi-org / subsidiaries", "Department budgets", "Segregation of duties", "Priority support"],
  },
  {
    plan: "Enterprise", monthly: 0, annualMonthly: 0, featured: false, contactSales: true,
    features: ["Everything in Business", "SSO / SAML", "Custom ERP integrations", "Dedicated SLA", "Data residency"],
  },
];

export default function LandingPage() {
  const { isAuthenticated } = useAppStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const [navScrolled, setNavScrolled] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [stepsPaused, setStepsPaused] = useState(false);
  const [pricingAnnual, setPricingAnnual] = useState(false);

  useEffect(() => {
    function onScroll() {
      setNavScrolled(window.scrollY > 8);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (stepsPaused) return;
    const id = setInterval(() => {
      setActiveStep((s) => (s + 1) % WORKFLOW_STEPS.length);
    }, 4200);
    return () => clearInterval(id);
  }, [stepsPaused]);

  const closeMenu = () => setMenuOpen(false);

  return (
    <main className="landing">
      {/* ── Nav — v3 pattern: inline desktop links, full-screen mobile takeover ── */}
      <nav className={`nav${navScrolled ? " nav-scrolled" : ""}`} style={navScrolled ? { boxShadow: "0 4px 24px rgba(26,25,22,0.05)" } : undefined}>
        <Link href="/" className="nav-logo serif" onClick={closeMenu}>
          Invoi<span>AI</span>
        </Link>
        <div className="nav-links">
          <a href="#product" className="nav-link">Product</a>
          <a href="#integrations" className="nav-link">Integrations</a>
          <a href="#pricing" className="nav-link">Pricing</a>
          <Link href="/docs" className="nav-link">Docs</Link>
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

      <MobileMenu
        open={menuOpen}
        onClose={closeMenu}
        links={[
          { href: "#product", label: "Product" },
          { href: "#workflow", label: "How it works" },
          { href: "#gl-coding", label: "GL coding" },
          { href: "#integrations", label: "Integrations" },
          { href: "#pricing", label: "Pricing" },
          { href: "/docs", label: "Docs" },
        ]}
        ctaHref="/signup"
        ctaLabel="Get started"
        secondaryHref={isAuthenticated ? "/dashboard" : "/login"}
        secondaryLabel={isAuthenticated ? "Go to dashboard" : "Sign in"}
      />

      {/* ═══════════════════════════════════════
          HERO + FEATURE STRIP — approved design,
          left exactly as it was handed over.
          ═══════════════════════════════════════ */}
      <section className="hero-new">
        <div className="hero-copy">
          <div className="eyebrow">Finance operations, without the spreadsheet chase</div>
          <h1>
            From invoice
            <br />
            <em>to decision.</em>
          </h1>
          <p>
            InvoiAI reads incoming invoices, checks what matters, matches them to POs and
            receipts, suggests the right accounting code, and routes only the work that
            needs a human.
          </p>
          <div className="hero-actions">
            <Link href="/signup" className="btn-primary">
              Start free <ArrowRight size={16} />
            </Link>
            <Link href="/docs" className="btn-quiet">See how it works</Link>
          </div>
          <div className="hero-proof">
            <span><Check size={14} /> Upload or email</span>
            <span><Check size={14} /> 2 & 3-way matching</span>
            <span><Check size={14} /> QuickBooks ready</span>
          </div>
        </div>
        <div className="decision-ledger">
          <div className="ledger-top">
            <span>INVOIAI / DECISION</span>
            <span>INV-2048</span>
          </div>
          <div className="invoice-visual">
            <div>
              <small>VENDOR</small>
              <strong>Acme Industrial Supply</strong>
            </div>
            <div className="amount">$8,420.00</div>
            <div className="line"><span>PO match</span><b className="good">Matched</b></div>
            <div className="line"><span>Receipt</span><b className="good">Matched</b></div>
            <div className="line"><span>GL coding</span><b className="code">5200 · Materials</b></div>
            <div className="line"><span>Risk</span><b className="good">Low</b></div>
          </div>
          <div className="ledger-stamp">
            <ShieldCheck size={15} /> Ready for approval
          </div>
        </div>
      </section>

      <section id="features" className="feature-strip">
        <Feature icon={<Mail />} title="Invoice inbox" text="Forward supplier invoices into one controlled intake." />
        <Feature icon={<GitCompareArrows />} title="2 / 3-way matching" text="Compare invoice, PO and receipt evidence." />
        <Feature icon={<BookOpenCheck />} title="GL coding" text="Code against the customer's existing accounts." />
        <Feature icon={<ShieldCheck />} title="Exception control" text="Escalate mismatches instead of hiding them." />
      </section>

      {/* ═══════════════════════════════════════
          Everything from here down is new.
          ═══════════════════════════════════════ */}

      {/* Trust band + quick stats */}
      <div className="trust-band">
        <div className="trust-band-label">Built for teams already running on QuickBooks or Xero</div>
        <div className="trust-row">
          {["Contractors", "Agencies", "Ecommerce", "Wholesalers", "Professional services", "Independent finance teams"].map((t, i, arr) => (
            <span key={t} style={{ display: "flex", alignItems: "center" }}>
              <span className="trust-pill">{t}</span>
              {i < arr.length - 1 && <span className="trust-dot">·</span>}
            </span>
          ))}
        </div>
      </div>
      <div className="stat-strip">
        <StatCounter value={8} label="Verification checks per document" />
        <StatCounter value={3} label="Coding tiers before a human is asked" />
        <StatCounter value={12} label="Industries with tuned extraction" />
        <StatCounter value={2} label="Accounting platforms, two-way sync" />
      </div>

      {/* Product principles */}
      <div id="product" className="how-section" style={{ borderTop: "none" }}>
        <div className="section-label">§01 What InvoiAI actually does</div>
        <Reveal>
          <h2 className="serif" style={{ fontSize: 36, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 12 }}>
            Four jobs. One finance layer.
          </h2>
          <p style={{ fontSize: 15, color: "#6B6860", maxWidth: 580, marginBottom: 40, lineHeight: 1.7 }}>
            Extraction alone just gets you structured data sitting in a database.
            InvoiAI goes further than that. It decides whether a document can be
            trusted, works out where it belongs in your books, keeps your accounting
            platform in sync, and tells you what is about to go wrong before you ask.
          </p>
        </Reveal>
        <div className="principles" style={{ marginTop: 0 }}>
          {[
            { num: "§01-01", Icon: ScanLine, title: "Reads anything", desc: "Invoices, receipts, bills, purchase orders and bank statements. Digital or scanned, nothing gets rekeyed by hand." },
            { num: "§01-02", Icon: GitCompareArrows, title: "Matches the evidence", desc: "Two and three-way matching against purchase orders and goods receipts, with tolerances you set, not a blunt total comparison." },
            { num: "§01-03", Icon: BookOpenCheck, title: "Codes it correctly", desc: "Coding rules, vendor history and a model, in that order, land every line on the right account, department, project or tax code." },
            { num: "§01-04", Icon: TrendingUp, title: "Watches proactively", desc: "A daily insight pass flags cash runway risk, overdue invoices, price hikes and duplicate charges before you go looking." },
          ].map((p, i) => (
            <Reveal key={p.title} delay={i * 90} className="principle-card">
              <div className="principle-num">{p.num}</div>
              <div className="principle-icon">
                <p.Icon size={18} />
              </div>
              <div className="principle-title serif">{p.title}</div>
              <div className="principle-desc">{p.desc}</div>
            </Reveal>
          ))}
        </div>
      </div>

      {/* ═══════════════════════════════════════
          How it works — interactive 7-step flow
          ═══════════════════════════════════════ */}
      <div id="workflow" className="how-section">
        <div className="section-label">§02 Your workflow</div>
        <Reveal>
          <h2 className="serif" style={{ fontSize: 36, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 16 }}>
            Seven steps.
            <br />Zero manual entry.
          </h2>
          <p style={{ fontSize: 15, color: "#6B6860", maxWidth: 480, marginBottom: 48, lineHeight: 1.7 }}>
            This is exactly what happens between the moment an invoice lands and
            the moment it is sitting, coded and synced, in your books. Click a
            step, or let it run on its own.
          </p>
        </Reveal>

        <div
          className="workflow-grid"
          onMouseEnter={() => setStepsPaused(true)}
          onMouseLeave={() => setStepsPaused(false)}
        >
          <Reveal className="workflow-steps" role="tablist" aria-label="InvoiAI workflow steps">
            {WORKFLOW_STEPS.map((step, i) => {
              const StepIcon = step.icon;
              const isActive = i === activeStep;
              return (
                <button
                  key={step.n}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`workflow-step${isActive ? " active" : ""}`}
                  onClick={() => setActiveStep(i)}
                >
                  <div className="workflow-step-num">
                    {isActive ? <StepIcon size={15} /> : step.n}
                  </div>
                  <div className="workflow-step-body">
                    <div className="workflow-step-title">{step.title}</div>
                    <div className="workflow-step-desc">{step.desc}</div>
                    <div className="workflow-step-progress">
                      {isActive && (
                        <div
                          key={activeStep}
                          className="workflow-step-progress-fill"
                          style={{ animationPlayState: stepsPaused ? "paused" : "running" }}
                        />
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </Reveal>

          <Reveal delay={120}>
            <div className="workflow-visual" role="tabpanel" aria-live="polite">
              <div className="workflow-visual-label">
                Step {WORKFLOW_STEPS[activeStep].n} · {WORKFLOW_STEPS[activeStep].title}
              </div>

              <div key={activeStep} className="workflow-visual-body">
                {activeStep === 0 && (
                  <div className="upload-zone" style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
                    <UploadCloud size={28} style={{ margin: "0 auto 12px", color: "#C8922A" }} />
                    <div style={{ fontWeight: 500, color: "#1A1916", marginBottom: 4, fontSize: 13 }}>
                      Drop any financial document
                    </div>
                    <div style={{ fontSize: 12 }}>Invoice · Receipt · Bill · PO · Bank statement</div>
                  </div>
                )}

                {activeStep === 1 && (
                  <div>
                    {[["Vendor", "Acme Corp Ltd"], ["Invoice No.", "INV-2026-0042"], ["Date", "March 1, 2026"], ["Total Due", "$2,231.25"]].map(([k, v], i) => (
                      <div key={k} className="result-row" style={{ opacity: 0, animation: `itemIn 0.4s var(--ease-out) ${i * 0.1}s forwards` }}>
                        <span className="result-key">{k}</span>
                        <span className="result-val">{v}</span>
                      </div>
                    ))}
                    <div className="confidence-badge" style={{ opacity: 0, animation: "itemIn 0.4s var(--ease-out) 0.5s forwards" }}>
                      <Sparkles size={12} /> Extracted, industry-tuned model
                    </div>
                  </div>
                )}

                {activeStep === 2 && (
                  <div className="verify-list">
                    {[
                      { label: "PO-1188 · 40 steel brackets", status: "Matched" },
                      { label: "GR-0451 · received Mar 3", status: "Matched" },
                      { label: "Unit price variance", status: "0.4% · within range" },
                    ].map((c, i) => (
                      <div key={c.label} className="verify-item" style={{ animationDelay: `${i * 0.08}s` }}>
                        <span className="verify-item-name"><CheckCircle2 size={13} color="#1E7E4B" /> {c.label}</span>
                        <span className="verify-item-status pass">{c.status}</span>
                      </div>
                    ))}
                  </div>
                )}

                {activeStep === 3 && (
                  <div className="coding-panel" style={{ border: "none" }}>
                    {CODING_ROWS.slice(0, 2).map((row, i) => (
                      <div key={row.item} className="coding-row" style={{ opacity: 0, animation: `itemIn 0.4s var(--ease-out) ${i * 0.1}s forwards` }}>
                        <div>
                          <div className="coding-item">{row.item}</div>
                          <div className="coding-account">{row.account}</div>
                          <div className="coding-meter-wrap">
                            <div className="coding-meter"><div className={`coding-meter-fill ${row.tone}`} style={{ width: `${row.pct}%` }} /></div>
                            <span className="coding-pct">{row.pct}%</span>
                          </div>
                        </div>
                        <span className={`coding-source ${row.tone}`}>{row.source}</span>
                      </div>
                    ))}
                  </div>
                )}

                {activeStep === 4 && (
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
                      <HealthGauge score={94} size={64} stroke={6} triggerKey={activeStep} />
                      <div>
                        <div className="risk-badge low"><span className="risk-badge-dot" /> Low risk</div>
                        <div style={{ fontSize: 11, color: "#6B6860", marginTop: 6 }}>Recommendation: auto-approve</div>
                      </div>
                    </div>
                    <div className="verify-list">
                      {VERIFY_CHECKS.map((c, i) => (
                        <div key={c.label} className="verify-item" style={{ animationDelay: `${i * 0.08}s` }}>
                          <span className="verify-item-name"><CheckCircle2 size={13} color="#1E7E4B" /> {c.label}</span>
                          <span className="verify-item-status pass">Passed</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeStep === 5 && (
                  <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
                    <div className="approval-card-row">
                      <div className="approval-avatar">ST</div>
                      <div>
                        <div className="approval-info-name">Sarah T.</div>
                        <div className="approval-info-role">Finance manager · Approver</div>
                      </div>
                    </div>
                    <div className="approval-limit-note">
                      $2,231.25 exceeds the $2,000 auto-approve threshold, so it is
                      routed for review. A reminder goes out in 24 hours if nobody
                      touches it.
                    </div>
                    <div className="approval-btn-row">
                      <div className="approval-btn approve">Approve</div>
                      <div className="approval-btn reject">Reject</div>
                    </div>
                  </div>
                )}

                {activeStep === 6 && (
                  <div>
                    {[
                      { name: "QuickBooks", status: "Synced" },
                      { name: "Insight engine", status: "Scanning" },
                      { name: "Finance Copilot", status: "Ready" },
                    ].map((s, i) => (
                      <div key={s.name} className="sync-item" style={{ animationDelay: `${i * 0.1}s` }}>
                        <span className="sync-item-name">
                          <span className="sync-item-icon"><FileText size={13} /></span>
                          {s.name}
                        </span>
                        <span className="sync-item-status"><CheckCircle2 size={12} /> {s.status}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Reveal>
        </div>
      </div>

      {/* ═══════════════════════════════════════
          GL Coding — dedicated deep dive
          ═══════════════════════════════════════ */}
      <div id="gl-coding" className="gl-section">
        <div className="section-label">§03 GL Coding</div>
        <div className="gl-layout">
          <Reveal>
            <h2 className="serif" style={{ fontSize: 34, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 16 }}>
              Coding that explains<br />where a number came from.
            </h2>
            <p style={{ fontSize: 15, color: "#6B6860", lineHeight: 1.7, maxWidth: 460 }}>
              Most tools guess at an account and move on. InvoiAI works down
              a strict order instead, and every line item keeps a record of
              which tier decided it. Nothing is coded silently.
            </p>
            <div className="gl-tiers">
              <div className="gl-tier">
                <div className="gl-tier-num">1</div>
                <div className="gl-tier-text">
                  <strong>Your coding rules first</strong>
                  <span>Rules you set for a vendor, category or keyword are checked before anything else. A match here is treated as settled.</span>
                </div>
              </div>
              <div className="gl-tier">
                <div className="gl-tier-num">2</div>
                <div className="gl-tier-text">
                  <strong>Then your own history</strong>
                  <span>If no rule fires, InvoiAI looks at how you coded similar line items from that same vendor in the past and follows the pattern.</span>
                </div>
              </div>
              <div className="gl-tier">
                <div className="gl-tier-num">3</div>
                <div className="gl-tier-text">
                  <strong>A model fills the gap</strong>
                  <span>Only once rules and history come up empty does a model suggest an account, and it is marked clearly as a suggestion, not a fact.</span>
                </div>
              </div>
            </div>
            <p style={{ fontSize: 13, color: "#6B6860", lineHeight: 1.7, marginTop: 24, maxWidth: 460 }}>
              Every account, department, cost center, project and tax code
              comes from your actual chart of accounts, synced live from
              QuickBooks or Xero. Nothing is a canned list.
            </p>
          </Reveal>

          <Reveal delay={120}>
            <div className="coding-panel">
              {CODING_ROWS.map((row) => (
                <div key={row.item} className="coding-row">
                  <div>
                    <div className="coding-item">{row.item}</div>
                    <div className="coding-account">{row.account}</div>
                    <div className="coding-meter-wrap">
                      <div className="coding-meter"><div className={`coding-meter-fill ${row.tone}`} style={{ width: `${row.pct}%` }} /></div>
                      <span className="coding-pct">{row.pct}%</span>
                    </div>
                  </div>
                  <span className={`coding-source ${row.tone}`}>{row.source}</span>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </div>

      {/* ═══════════════════════════════════════
          Matching & exceptions
          ═══════════════════════════════════════ */}
      <div id="matching" className="match-section">
        <div className="section-label">§04 Matching & Exceptions</div>
        <Reveal>
          <h2 className="serif" style={{ fontSize: 34, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 12 }}>
            Disagreements get a reason,<br />not a shrug.
          </h2>
          <p style={{ fontSize: 15, color: "#6B6860", maxWidth: 580, lineHeight: 1.7 }}>
            A total that matches is not proof that an invoice is correct.
            InvoiAI compares quantities and unit prices against the purchase
            order and, where one exists, the goods receipt, and anything
            outside your tolerance gets pulled out and explained instead of
            averaged away.
          </p>
        </Reveal>
        <div className="match-layout">
          <div className="match-explain">
            <Reveal className="match-point">
              <div className="match-point-icon"><GitCompareArrows size={16} /></div>
              <div>
                <strong>Two-way matching</strong>
                <p>Invoice against purchase order, for line items without a physical delivery to confirm, like services or subscriptions.</p>
              </div>
            </Reveal>
            <Reveal delay={80} className="match-point">
              <div className="match-point-icon"><Layers size={16} /></div>
              <div>
                <strong>Three-way matching</strong>
                <p>Invoice, purchase order and goods receipt together, for anything physically received, so you never pay for what never arrived.</p>
              </div>
            </Reveal>
            <Reveal delay={160} className="match-point">
              <div className="match-point-icon"><ShieldCheck size={16} /></div>
              <div>
                <strong>Tolerance you control</strong>
                <p>Set how much price or quantity variance is acceptable. Inside it, invoices keep moving. Outside it, they stop for a reason.</p>
              </div>
            </Reveal>
          </div>
          <Reveal delay={100}>
            <div className="mkt-exception-queue">
              <div className="mkt-exception-queue-head">
                <span>Exception queue</span>
                <span>3 open</span>
              </div>
              {EXCEPTIONS.map((ex) => (
                <div key={ex.vendor} className="mkt-exception-card">
                  <div className="mkt-exception-top">
                    <span className="mkt-exception-vendor">{ex.vendor}</span>
                    <span className={`mkt-exception-severity ${ex.severity}`}>{ex.severity}</span>
                  </div>
                  <p className="mkt-exception-reason">{ex.reason}</p>
                  <div className="mkt-exception-actions">
                    <span className="mkt-exception-action primary">Review</span>
                    <span className="mkt-exception-action">Send back</span>
                  </div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </div>

      {/* ═══════════════════════════════════════
          Integrations
          ═══════════════════════════════════════ */}
      <div id="integrations" className="integrations-section">
        <div className="section-label">§05 Integrations</div>
        <Reveal>
          <h2 className="serif" style={{ fontSize: 36, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 12 }}>
            Your books, always current.
          </h2>
          <p style={{ fontSize: 15, color: "#6B6860", maxWidth: 560, lineHeight: 1.7 }}>
            Connect once. InvoiAI normalizes every vendor, customer, invoice,
            bill, payment and purchase order into the same domain model,
            no matter which platform it came from.
          </p>
        </Reveal>
        <div className="integrations-grid">
          {INTEGRATIONS.map((it, i) => (
            <Reveal key={it.name} delay={i * 80} className="integration-card">
              <div className="integration-card-icon"><it.icon size={18} /></div>
              <div className="integration-card-name">{it.name}</div>
              <div className="integration-card-desc">{it.desc}</div>
              <div className={`integration-card-status${it.live ? " live" : ""}`}>
                <span className="risk-badge-dot" style={{ background: it.live ? "#1E7E4B" : "#AAA8A0" }} /> {it.status}
              </div>
            </Reveal>
          ))}
        </div>
      </div>

      {/* ═══════════════════════════════════════
          Insights preview
          ═══════════════════════════════════════ */}
      <div id="insights" className="insights-section">
        <div className="section-label">§06 Proactive insights</div>
        <Reveal>
          <h2 className="serif" style={{ fontSize: 36, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 12 }}>
            It tells you before you have to ask.
          </h2>
          <p style={{ fontSize: 15, color: "#6B6860", maxWidth: 560, lineHeight: 1.7 }}>
            A daily analyzer pass, pure math and no model involved, runs
            against your synced data: cash runway, overdue receivables,
            vendor price trends, spending anomalies, duplicate charges.
            What it finds shows up as a plain-English feed, ranked by
            how much it matters.
          </p>
        </Reveal>
        <div className="insights-grid">
          {INSIGHTS_PREVIEW.map((ins, i) => (
            <Reveal key={ins.title} delay={i * 80} className="insight-card">
              <div className={`insight-card-icon ${ins.tone}`}><ins.icon size={16} /></div>
              <div>
                <div className={`insight-card-severity ${ins.tone}`}>{ins.severity}</div>
                <div className="insight-card-title">{ins.title}</div>
                <div className="insight-card-action">Suggested: {ins.action}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>

      {/* ═══════════════════════════════════════
          Finance Copilot
          ═══════════════════════════════════════ */}
      <div id="copilot" className="copilot-section">
        <div className="section-label">§07 Finance Copilot</div>
        <div className="copilot-layout">
          <Reveal>
            <h2 className="serif" style={{ fontSize: 32, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 16 }}>
              Ask it anything.<br />It never guesses the numbers.
            </h2>
            <p style={{ fontSize: 15, color: "#6B6860", lineHeight: 1.7, maxWidth: 440 }}>
              The Copilot explains, it does not calculate on the fly. It
              calls the same deterministic analyzers that feed your insight
              feed, gets back real computed facts, and only then puts them
              into plain English. It never queries your data directly.
            </p>
            <div className="copilot-feature-list">
              <div className="copilot-feature-item">
                <div className="copilot-feature-icon"><ShieldCheck size={14} /></div>
                <div className="copilot-feature-text"><strong>Grounded, not generated.</strong> Every number traces back to a real analyzer run against your data.</div>
              </div>
              <div className="copilot-feature-item">
                <div className="copilot-feature-icon"><RefreshCw size={14} /></div>
                <div className="copilot-feature-text"><strong>Same engine, two audiences.</strong> Business tools for vendors and cashflow, personal tools for budgets and debt payoff.</div>
              </div>
              <div className="copilot-feature-item">
                <div className="copilot-feature-icon"><MessageSquare size={14} /></div>
                <div className="copilot-feature-text"><strong>Takes action.</strong> Draft a follow-up email to an overdue customer, right from the chat.</div>
              </div>
            </div>
          </Reveal>

          <Reveal delay={120}>
            <div className="copilot-window">
              <div className="copilot-window-bar">
                <MessageSquare size={13} /> Finance Copilot
              </div>
              <div className="copilot-body">
                <div className="copilot-bubble user" style={{ animationDelay: "0.1s" }}>
                  Which vendor raised prices the most this month?
                </div>
                <div className="copilot-bubble assistant" style={{ animationDelay: "0.5s" }}>
                  <div className="copilot-fact-tag"><Sparkles size={10} /> Computed by vendor_analyzer</div>
                  Acme Steel is up 14%. Their 12-month average was $1,200,
                  the last invoice was $1,370. That is 2.1 standard
                  deviations above normal, worth getting a comparison
                  quote for.
                </div>
                <div className="copilot-bubble user" style={{ animationDelay: "0.9s" }}>
                  Got paid $2,400 today, also spent $45 on fuel
                </div>
                <div className="copilot-bubble assistant" style={{ animationDelay: "1.3s" }}>
                  <div className="copilot-fact-tag"><Sparkles size={10} /> Computed by planning_service</div>
                  Logged both. After this month's bills and debt minimums,
                  you have $735 left. I would put $300 extra on the credit
                  card, $200 into savings, and leave $235 flexible.
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </div>

      {/* ═══════════════════════════════════════
          Workspaces: Business vs Personal
          ═══════════════════════════════════════ */}
      <div className="audience-section">
        <div className="section-label">§08 Built for both</div>
        <Reveal>
          <h2 className="serif" style={{ fontSize: 36, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 12 }}>
            One account. Separate workspaces.
          </h2>
          <p style={{ fontSize: 15, color: "#6B6860", maxWidth: 560, lineHeight: 1.7, marginBottom: 40 }}>
            Every workspace, business or personal, is its own isolated
            tenant behind the scenes. You can hold one personal workspace
            and as many business ones as you run, and nothing about the
            data in one is ever visible from another.
          </p>
        </Reveal>
        <div className="audience-grid">
          <Reveal className="audience-card">
            <span className="audience-tag"><Building2 size={11} style={{ verticalAlign: -1, marginRight: 4 }} />Business</span>
            <div className="audience-title serif">Run finance without a finance department</div>
            <p className="audience-desc">
              For contractors, agencies, ecommerce, wholesalers and
              professional services running on QuickBooks or Xero without
              a dedicated controller on staff.
            </p>
            <div className="audience-list">
              {["Document verification and approval routing", "GL coding against your real chart of accounts", "Vendor risk, duplicates and 3-way matching", "Role-based teams with spending limits"].map((t) => (
                <div key={t} className="audience-list-item"><CheckCircle2 size={14} /> {t}</div>
              ))}
            </div>
          </Reveal>
          <Reveal delay={100} className="audience-card dark">
            <span className="audience-tag"><User size={11} style={{ verticalAlign: -1, marginRight: 4 }} />Personal</span>
            <div className="audience-title serif">A budget that updates itself</div>
            <p className="audience-desc">
              For individuals who would rather text their spending than
              track it by hand. Log income and expenses in plain language,
              or upload a bank statement.
            </p>
            <div className="audience-list">
              {["Auto-categorized bank statement import", "Weekly allocation plans built from real income", "Debt payoff strategy and goal tracking", "Same Copilot, tuned for personal finance"].map((t) => (
                <div key={t} className="audience-list-item"><CheckCircle2 size={14} /> {t}</div>
              ))}
            </div>
          </Reveal>
        </div>
      </div>

      {/* ═══════════════════════════════════════
          Industries
          ═══════════════════════════════════════ */}
      <div id="industries" className="industries-section">
        <div className="section-label">§09 Industries</div>
        <Reveal>
          <h2 className="serif" style={{ fontSize: 32, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 12 }}>
            Extraction tuned per industry, not a generic template.
          </h2>
          <p style={{ fontSize: 15, color: "#6B6860", maxWidth: 560, lineHeight: 1.7 }}>
            A retail receipt, a construction pay application and a
            healthcare statement do not share a shape. Pick your industry
            once and the extraction, the coding rules and the risk checks
            all adjust to match it.
          </p>
        </Reveal>
        <div className="industries-belt">
          {INDUSTRIES.map((ind) => (
            <span key={ind} className="industry-chip">{ind}</span>
          ))}
        </div>
      </div>

      {/* ═══════════════════════════════════════
          Security & trust
          ═══════════════════════════════════════ */}
      <div className="how-section">
        <div className="section-label">§10 Security & trust</div>
        <Reveal>
          <h2 className="serif" style={{ fontSize: 32, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 12 }}>
            Boring in the right places.
          </h2>
          <p style={{ fontSize: 15, color: "#6B6860", maxWidth: 560, marginBottom: 40, lineHeight: 1.7 }}>
            Nothing about how InvoiAI handles your data is meant to be
            exciting. It is meant to hold up.
          </p>
        </Reveal>
        <div className="principles" style={{ marginTop: 0 }}>
          {[
            { num: "§10-01", Icon: ShieldCheck, title: "Real tenant isolation", desc: "Every request carries a workspace ID that is checked server side against your actual membership. The header selects a tenant, it never authorizes one on its own." },
            { num: "§10-02", Icon: KeyRound, title: "Encrypted credentials", desc: "QuickBooks and Xero tokens are stored encrypted at rest, never exposed through the API, and scoped to a single workspace." },
            { num: "§10-03", Icon: UserCheck, title: "Approval limits that hold", desc: "Spending thresholds are enforced per role, not just suggested, so nothing above a limit clears without the right person seeing it." },
            { num: "§10-04", Icon: History, title: "A durable audit trail", desc: "Every decision, edit and sync is logged with who and when, so a question about a number six months from now still has an answer." },
          ].map((p, i) => (
            <Reveal key={p.title} delay={i * 90} className="principle-card">
              <div className="principle-num">{p.num}</div>
              <div className="principle-icon">
                <p.Icon size={18} />
              </div>
              <div className="principle-title serif">{p.title}</div>
              <div className="principle-desc">{p.desc}</div>
            </Reveal>
          ))}
        </div>
      </div>

      {/* ── Pricing ── */}
      <div id="pricing" className="pricing-section">
        <div className="section-label">§11 Pricing</div>
        <Reveal>
          <h2 className="serif" style={{ fontSize: 36, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 12 }}>
            Free is enough to feel it. Paid is enough to run on.
          </h2>
          <p style={{ fontSize: 15, color: "#6B6860", maxWidth: 560, lineHeight: 1.7 }}>
            Fifteen documents a month is enough to process a small
            business's bills, watch the verification and matching engine
            work, and connect QuickBooks or Xero. It is not enough to run
            on indefinitely, on purpose.
          </p>
        </Reveal>

        <div style={{ display: "flex", justifyContent: "center" }}>
          <div className="pricing-toggle">
            <button type="button" className={`pricing-toggle-btn${!pricingAnnual ? " active" : ""}`} onClick={() => setPricingAnnual(false)}>Monthly</button>
            <button type="button" className={`pricing-toggle-btn${pricingAnnual ? " active" : ""}`} onClick={() => setPricingAnnual(true)}>
              Annual <span className="pricing-toggle-save">Save ~18%</span>
            </button>
          </div>
        </div>

        <div className="pricing-grid tiers-5" style={{ marginTop: 20 }}>
          {PRICING_TIERS.map((p, i) => (
            <Reveal key={p.plan} delay={i * 70} className={`pricing-card${p.featured ? " featured" : ""}`}>
              <div className="pricing-plan">{p.plan}</div>
              {p.contactSales ? (
                <div className="pricing-contact-price">Contact us</div>
              ) : (
                <div className="pricing-price-row">
                  <div className="pricing-price serif">${pricingAnnual ? p.annualMonthly : p.monthly}</div>
                  {pricingAnnual && p.annualMonthly !== p.monthly && <span className="pricing-price-was">${p.monthly}</span>}
                </div>
              )}
              <div className="pricing-period">{p.contactSales ? "custom contract" : p.monthly === 0 ? "forever" : pricingAnnual ? "per month, billed annually" : "per month"}</div>
              {p.features.map((f) => (
                <div key={f} className="pricing-feature">{f}</div>
              ))}
              {p.contactSales ? (
                <a href="mailto:sales@invoiai.com?subject=Enterprise%20plan" className="pricing-btn" style={{ textDecoration: "none", display: "block", textAlign: "center" }}>
                  Contact sales
                </a>
              ) : (
                <Link href="/signup" className="pricing-btn" style={{ textDecoration: "none", display: "block", textAlign: "center" }}>
                  {p.featured ? "Get started →" : "Start free"}
                </Link>
              )}
            </Reveal>
          ))}
        </div>
        <Reveal delay={200}>
          <div style={{ marginTop: 28, textAlign: "center", fontSize: 13, color: "#6B6860" }}>
            Managing your own money too? Every business plan from Starter up
            unlocks the personal workspace fully,{" "}
            <Link href="/signup" style={{ color: "#C8922A" }}>see how it works →</Link>
          </div>
        </Reveal>
      </div>

      {/* ── Final CTA band ── */}
      <Reveal>
        <div className="cta-band">
          <div className="cta-band-inner">
            <div className="cta-band-title serif">Stop finding out too late.</div>
            <p className="cta-band-sub">
              Every document gets a health score, a match result, a GL code
              and a risk level, while an insight engine keeps watching
              everything else.
            </p>
            <Link href="/signup" className="cta-band-btn">
              Start free, no card needed <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </Reveal>

      {/* Footer */}
      <div style={{ borderTop: "0.5px solid #E2DDD4" }}>
        <div className="footer">
          <div className="footer-logo serif">Invoi<span>AI</span></div>
          <div className="footer-links">
            <a href="#product" className="footer-link">Product</a>
            <a href="#gl-coding" className="footer-link">GL coding</a>
            <a href="#integrations" className="footer-link">Integrations</a>
            <a href="#pricing" className="footer-link">Pricing</a>
            <Link href="/docs" className="footer-link">Docs</Link>
          </div>
          <div className="footer-text">© 2026 InvoiAI · Invoice intelligence, AP automation, personal finance.</div>
        </div>
      </div>
    </main>
  );
}
