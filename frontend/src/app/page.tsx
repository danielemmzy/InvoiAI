"use client";
// Landing Page — /

import Link from "next/link";
import { useAppStore } from "@/store/useAppStore";

export default function LandingPage() {
  const { isAuthenticated } = useAppStore();

  return (
    <div style={{ background: "#F7F4EE", minHeight: "100vh" }}>

      {/* ── Navbar ── */}
      <nav className="nav">
        <Link href="/" className="nav-logo serif">
          Invoi<span>AI</span>
        </Link>
        <div className="nav-links">
          <span className="nav-link">Pricing</span>
          <span className="nav-link">Industries</span>
          <span className="nav-link">Docs</span>
          {isAuthenticated ? (
            <Link href="/dashboard" className="nav-cta">Dashboard →</Link>
          ) : (
            <>
              <Link href="/login" className="nav-link">Sign in</Link>
              <Link href="/signup" className="nav-cta">Get started →</Link>
            </>
          )}
        </div>
      </nav>

      {/* ── Hero ── */}
      <div className="hero">
        <div className="section-label">§00 Document Intelligence</div>

        <h1 className="hero-headline serif">
          Any invoice, any industry,<br />
          structured <span className="accent">instantly.</span>
        </h1>

        <p className="hero-sub">
          Upload a PDF, image, or scan. InvoiAI reads the document,
          detects the industry, and extracts every field —
          ready for Excel, CSV, or Google Sheets.
        </p>

        <div className="hero-actions">
          <Link href="/signup" className="btn-primary">
            Start free — no card needed
          </Link>
          <button className="btn-secondary">Watch 60s demo</button>
        </div>

        {/* Demo window */}
        <div className="demo-window">
          <div className="demo-bar">
            <div className="dot" style={{ background: "#E57373" }} />
            <div className="dot" style={{ background: "#FFB74D" }} />
            <div className="dot" style={{ background: "#81C784" }} />
            <span style={{ marginLeft: 8, fontSize: 11, color: "#6B6860" }}>
              InvoiAI — Upload & Extract
            </span>
          </div>
          <div className="demo-content">
            <div className="demo-left">
              <div className="upload-zone">
                <div style={{ fontSize: 28, marginBottom: 10 }}>📄</div>
                <div style={{ fontWeight: 500, color: "#1A1916", marginBottom: 4, fontSize: 13 }}>
                  Drop invoice here
                </div>
                <div style={{ fontSize: 12 }}>PDF · JPG · PNG · WEBP · up to 10MB</div>
              </div>
              <div className="industry-select">
                <span style={{ fontSize: 13 }}>Accounting</span>
                <span style={{ fontSize: 11, color: "#6B6860" }}>▾</span>
              </div>
              <button className="extract-btn">Extract structured data →</button>
            </div>
            <div className="demo-right">
              <div className="result-label">Extracted — Invoice · High confidence</div>
              {[
                ["Vendor", "Acme Corp Ltd"],
                ["Invoice No.", "INV-2026-0042"],
                ["Date", "March 1, 2026"],
                ["Due Date", "March 15, 2026"],
                ["Subtotal", "$2,125.00"],
                ["Tax (5%)", "$106.25"],
                ["Total Due", "$2,231.25"],
              ].map(([k, v]) => (
                <div key={k} className="result-row">
                  <span className="result-key">{k}</span>
                  <span className="result-val">{v}</span>
                </div>
              ))}
              <div className="confidence-badge">✓ Validation passed · 0 warnings</div>
              <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                {["↓ Excel", "↓ CSV", "→ Sheets"].map((l) => (
                  <div key={l} style={{ flex: 1, textAlign: "center", padding: "7px 4px", border: "0.5px solid #E2DDD4", borderRadius: 5, fontSize: 11, color: "#6B6860", cursor: "pointer" }}>
                    {l}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Principles */}
        <div className="section-label">§01 What InvoiAI Is About</div>
        <h2 className="serif" style={{ fontSize: 36, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 40 }}>
          Built for professionals<br />who handle documents daily.
        </h2>
        <div className="principles">
          {[
            { num: "§01-01 · PRINCIPLE 01", icon: "⚡", title: "Instant", desc: "Upload any invoice — digital PDF, phone photo, or scanned document. Results in under 5 seconds, every time." },
            { num: "§01-02 · PRINCIPLE 02", icon: "🏭", title: "Industry-aware", desc: "20 supported industries. Auditing, e-commerce, construction, healthcare and more. Fields adapt to your domain automatically." },
            { num: "§01-03 · PRINCIPLE 03", icon: "📊", title: "Export-ready", desc: "One click to Excel, CSV, or live Google Sheets. Perfectly shaped columns for your workflow — no cleanup required." },
          ].map((p) => (
            <div key={p.title} className="principle-card">
              <div className="principle-num">{p.num}</div>
              <div className="principle-icon">{p.icon}</div>
              <div className="principle-title serif">{p.title}</div>
              <div className="principle-desc">{p.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div className="how-section">
        <div className="section-label">§02 How It Works</div>
        <h2 className="serif" style={{ fontSize: 36, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916", marginBottom: 48 }}>
          Three steps.<br />Zero manual entry.
        </h2>
        <div className="how-grid">
          <div>
            {[
              { n: "01", t: "Upload any document", d: "PDF, JPG, PNG or WEBP. Digital invoices, phone photos, scanned receipts — all accepted." },
              { n: "02", t: "Select your industry", d: "Choose from 20 industries. The AI adapts to your domain's specific fields and terminology." },
              { n: "03", t: "Get structured data", d: "GPT-4o reads the document and returns every table and field — validated and ready." },
              { n: "04", t: "Export your way", d: "Download as Excel or CSV. Push directly to Google Sheets. Your data, your format." },
            ].map((s) => (
              <div key={s.n} className="step">
                <div className="step-num">{s.n}</div>
                <div>
                  <div className="step-title">{s.t}</div>
                  <div className="step-desc">{s.d}</div>
                </div>
              </div>
            ))}
          </div>
          <div className="step-visual">
            <div style={{ fontSize: 10, fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase", color: "#6B6860", marginBottom: 8 }}>
              Processing
            </div>
            {["File received", "Industry detected: Auditing", "GPT-4o extracting fields", "Validation passed", "Export ready"].map((s, i) => (
              <div key={i} className="process-step">
                <div className="process-check">✓</div>
                <span className="process-label">{s}</span>
              </div>
            ))}
            <div className="result-summary" style={{ marginTop: "auto" }}>
              <div style={{ fontSize: 10, color: "#6B6860", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>Result</div>
              <div className="result-amount serif">$2,231.25</div>
              <div className="result-sub">Total amount due · 3 line items</div>
            </div>
          </div>
        </div>
      </div>

      {/* Pricing */}
      <div className="pricing-section">
        <div className="section-label">§03 Pricing</div>
        <h2 className="serif" style={{ fontSize: 36, fontWeight: 600, letterSpacing: -0.5, color: "#1A1916" }}>
          Start free. Scale when ready.
        </h2>
        <div className="pricing-grid">
          {[
            { plan: "Free", price: "$0", period: "forever", features: ["10 documents / month", "Excel & CSV export", "20 industries", "Basic history"], featured: false },
            { plan: "Starter", price: "$12", period: "per month", features: ["100 documents / month", "Excel, CSV & Google Sheets", "Priority extraction", "Full history"], featured: true },
            { plan: "Pro", price: "$29", period: "per month", features: ["500 documents / month", "API access", "All export formats", "Usage analytics"], featured: false },
          ].map((p) => (
            <div key={p.plan} className={`pricing-card${p.featured ? " featured" : ""}`}>
              <div className="pricing-plan">{p.plan}</div>
              <div className="pricing-price serif">{p.price}</div>
              <div className="pricing-period">{p.period}</div>
              {p.features.map((f) => (
                <div key={f} className="pricing-feature">{f}</div>
              ))}
              <Link href="/signup" className="pricing-btn" style={{ textDecoration: "none", display: "block", textAlign: "center" }}>
                {p.featured ? "Get started →" : "Start free"}
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div style={{ borderTop: "0.5px solid #E2DDD4", marginTop: 80 }}>
        <div className="footer">
          <div className="footer-logo serif">Invoi<span>AI</span></div>
          <div className="footer-text">© 2026 InvoiAI · Built for the people who build business.</div>
        </div>
      </div>
    </div>
  );
}