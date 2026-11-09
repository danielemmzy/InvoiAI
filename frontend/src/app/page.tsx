
"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, BookOpen, Building2, CheckCircle2, ChevronDown, CircleHelp, FileCheck2, FileText, GitCompareArrows, Landmark, Menu, Moon, ScanLine, ShieldCheck, Sparkles, Sun, Upload, UserRound, WalletCards, X } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import MotionMark from "@/components/ui/MotionMark";

const pulses = [
  { label: "Ready to approve", value: "12", detail: "Matched, coded, and inside policy." },
  { label: "Needs a look", value: "3", detail: "A clear exception is waiting for a decision." },
  { label: "Due this week", value: "$42k", detail: "Payables with a time-sensitive next step." },
];

const platform = [
  { icon: ScanLine, title: "Document intelligence", detail: "Read invoices, receipts, POs, statements, and supporting evidence." },
  { icon: GitCompareArrows, title: "AP automation", detail: "Match invoice, purchase order, and receipt before money moves." },
  { icon: ShieldCheck, title: "Approval control", detail: "Route bills by policy, authority, and exception without chasing people." },
  { icon: Landmark, title: "Accounting sync", detail: "Keep vendor, bill, payment, and purchase-order data connected." },
];

const workflow = ["Receive", "Extract", "Match", "Code", "Verify", "Approve", "Sync"];
const industries = ["General", "Retail", "Construction", "Healthcare", "Hospitality", "Manufacturing", "Professional services", "Real estate", "Technology", "Transportation", "Education", "Nonprofit"];
const plans = [
  { name: "Free", price: "$0", note: "Try the core flow", items: ["15 documents / month", "One accounting connection", "2-way matching"] },
  { name: "Starter", price: "$39", note: "For a focused finance team", items: ["100 documents / month", "AI GL coding", "Insights and exports"], featured: true },
  { name: "Pro", price: "$119", note: "For controlled AP", items: ["Unlimited documents", "3-way matching", "Email intake and audit trail"] },
  { name: "Business", price: "$349", note: "For complex organizations", items: ["Unlimited seats", "Multiple organizations", "Segregation of duties"] },
  { name: "Enterprise", price: "Let’s talk", note: "For tailored operations", items: ["Custom rollout", "Advanced controls", "Dedicated support"] },
];
const faqs = [
  ["What can InvoiAI receive?", "Invoices, receipts, bills, purchase orders, bank statements, and supporting documents."],
  ["Does it replace our accounting platform?", "No. It adds document intelligence and controls around your existing finance system, then keeps records in sync."],
  ["Can we separate business and personal finance?", "Yes. Workspaces are isolated, so your business operations and personal planning remain separate."],
  ["Can teams control who approves what?", "Yes. Roles, approval limits, escalation paths, and a durable audit trail are part of the operating model."],
];

export default function LandingPage() {
  const { isAuthenticated } = useAppStore();
  const [activePulse, setActivePulse] = useState(0);
  const [dark, setDark] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const startHref = isAuthenticated ? "/dashboard" : "/signup";

  return <main className={`fresh-landing${dark ? " fresh-dark" : ""}`}>
    <nav className="fresh-nav" aria-label="Primary navigation">
      <Link href="/" className="fresh-brand">invoi<span>ai</span></Link>
      <div className="fresh-nav-links">
        <a href="#features">Platform</a><a href="#workflows">Workflows</a><a href="#industry">Industry</a><a href="#pricing">Pricing</a>
        <button className="theme-toggle" type="button" onClick={() => setDark(!dark)} aria-label={`Switch to ${dark ? "light" : "dark"} theme`}>{dark ? <Sun size={16} /> : <Moon size={16} />}</button>
        <Link href="/login">Sign in</Link><Link href={startHref} className="fresh-nav-cta">{isAuthenticated ? "Open workspace" : "Request access"}</Link>
        <button className="fresh-menu-toggle" type="button" aria-label={menuOpen ? "Close navigation" : "Open navigation"} aria-expanded={menuOpen} aria-controls="mobile-navigation" onClick={() => setMenuOpen((open) => !open)}>{menuOpen ? <X size={19} /> : <Menu size={19} />}</button>
      </div>
    </nav>
    <nav id="mobile-navigation" className={`fresh-mobile-menu${menuOpen ? " is-open" : ""}`} aria-label="Mobile navigation">
      <a href="#features" onClick={() => setMenuOpen(false)}>Platform</a><a href="#workflows" onClick={() => setMenuOpen(false)}>Workflows</a><a href="#industry" onClick={() => setMenuOpen(false)}>Industry</a><a href="#pricing" onClick={() => setMenuOpen(false)}>Pricing</a>
      <Link href="/login" onClick={() => setMenuOpen(false)}>Sign in</Link><Link href={startHref} className="fresh-nav-cta" onClick={() => setMenuOpen(false)}>{isAuthenticated ? "Open workspace" : "Request access"}</Link>
    </nav>

    <section className="fresh-hero">
      <div className="fresh-hero-copy"><p className="fresh-kicker">Financial operations, kept human</p><h1>Move money with <em>context.</em></h1><p className="fresh-lede">InvoiAI turns every incoming document into a clear, controlled decision. Your team sees what matters, where it came from, and what should happen next.</p><div className="fresh-actions"><Link href={startHref} className="fresh-primary">{isAuthenticated ? "Open workspace" : "Start with your team"}<ArrowRight size={17} /></Link><a href="#control" className="fresh-text-link">See the control room</a></div><ul className="fresh-proof"><li><CheckCircle2 size={16} /> AP intake</li><li><CheckCircle2 size={16} /> Approval controls</li><li><CheckCircle2 size={16} /> Accounting sync</li></ul></div>
      <div className="hero-orbit" aria-label="Invoice decision preview"><div className="orbit-glow" /><div className="orbit-file orbit-file-back"><FileText size={24} /><span>PO 2048</span></div><div className="orbit-file orbit-file-front"><FileText size={28} /><strong>INV 2048</strong><span>Acme Industrial</span></div><div className="orbit-path"><i /><i /><i /><i /></div><div className="orbit-decision"><ShieldCheck size={18} /><span>Ready for review</span></div><div className="orbit-amount"><small>amount verified</small><strong>$8,420</strong></div><div className="hero-lottie" aria-hidden="true"><MotionMark /></div></div>
    </section>

    <section className="fresh-intro"><p>Finance should feel composed, not crowded.</p><h2>One clear workspace for every document, decision, and owner.</h2></section>

    <section id="features" className="platform-section"><div className="section-heading"><p className="fresh-kicker">Platform</p><h2>The operating layer around your books.</h2><p>Keep the context from your former InvoiAI experience, but give every capability a calmer place to live.</p></div><div className="platform-grid">{platform.map((item) => <article className="platform-card" key={item.title}><div className="capability-icon"><item.icon size={21} /></div><h3>{item.title}</h3><p>{item.detail}</p><a href="#workflows">Explore <ArrowRight size={14} /></a></article>)}</div></section>

    <section id="control" className="control-section"><div className="control-heading"><p className="fresh-kicker">The control room</p><h2>Less narration. More signal.</h2><p>Dashboard context appears when you hover, focus, or ask. The screen stays quiet until work needs attention.</p><Link href="/dashboard" className="fresh-text-link">Open the dashboard</Link></div><div className="control-board"><div className="control-board-top"><span>Today</span><span>Operating view</span></div><div className="control-pulse-row">{pulses.map((pulse, index) => <button key={pulse.label} type="button" className={`control-pulse${activePulse === index ? " active" : ""}`} onMouseEnter={() => setActivePulse(index)} onFocus={() => setActivePulse(index)} onClick={() => setActivePulse(index)} aria-pressed={activePulse === index}><span>{pulse.label}</span><strong>{pulse.value}</strong></button>)}</div><div className="control-explainer" role="status"><Sparkles size={18} /><span>{pulses[activePulse].detail}</span></div><div className="control-queue"><div className="queue-row emphasis"><span>Acme Industrial</span><span>PO + receipt matched</span><strong>$8,420</strong></div><div className="queue-row"><span>Northstar Supply</span><span>Owner needed</span><strong>$2,100</strong></div><div className="queue-row"><span>Horizon Freight</span><span>Due Friday</span><strong>$5,900</strong></div></div></div></section>

    <section id="workflows" className="workflow-section"><div className="section-heading"><p className="fresh-kicker">Workflows</p><h2>From arrival to accounted for.</h2><p>Each stage is connected. Your team steps in only where judgement is needed.</p></div><ol className="workflow-track">{workflow.map((step, index) => <li key={step}><span>{String(index + 1).padStart(2, "0")}</span><strong>{step}</strong>{index < workflow.length - 1 && <i />}</li>)}</ol><div className="workflow-anchors"><Link href="/dashboard/upload"><Upload size={18} /> Receive documents</Link><Link href="/dashboard/ap"><WalletCards size={18} /> Run AP control</Link><Link href="/dashboard/approvals"><FileCheck2 size={18} /> Review approvals</Link></div></section>

    <section id="business" className="business-section"><div className="business-copy"><p className="fresh-kicker">Business and personal</p><h2>One account. Separate financial worlds.</h2><p>Choose a business workspace for AP operations, or a personal workspace for everyday planning. Both stay deliberately separate.</p></div><div className="business-split"><article><Building2 size={22} /><h3>Business</h3><p>Vendors, POs, bills, approval authority, and a clear AP queue.</p><Link href="/dashboard">Business dashboard <ArrowRight size={15} /></Link></article><article><UserRound size={22} /><h3>Personal</h3><p>Income, expenses, budgets, bills, goals, and account planning.</p><Link href="/dashboard/personal">Personal workspace <ArrowRight size={15} /></Link></article></div></section>

    <section id="industry" className="industry-section"><div className="section-heading"><p className="fresh-kicker">Industry</p><h2>Recognize the shape of the work.</h2><p>Extraction, coding guidance, and control checks are designed to adapt to the industry you select.</p></div><div className="industry-belt">{industries.map((industry) => <span key={industry}>{industry}</span>)}</div></section>

    <section id="resources" className="resources-section"><div className="section-heading"><p className="fresh-kicker">Resources</p><h2>Bring your team up to speed.</h2></div><div className="resource-grid"><Link href="/docs"><BookOpen size={21} /><h3>Documentation</h3><p>Set up intake, workflows, integrations, and roles.</p><ArrowRight size={16} /></Link><Link href="/integrations"><Landmark size={21} /><h3>Integrations</h3><p>Connect the accounting system your team already uses.</p><ArrowRight size={16} /></Link><Link href="/dashboard"><CircleHelp size={21} /><h3>Workspace guide</h3><p>Open the dashboard and see each operating surface.</p><ArrowRight size={16} /></Link></div></section>

    <section id="pricing" className="pricing-section fresh-pricing"><div className="section-heading"><p className="fresh-kicker">Pricing</p><h2>Start small. Add control when you need it.</h2><p>Choose the plan that matches your finance operation today. Move up without rebuilding your workflow.</p></div><div className="fresh-pricing-grid">{plans.map((plan) => <article className={`fresh-price${plan.featured ? " featured" : ""}`} key={plan.name}>{plan.featured && <span>Most selected</span>}<h3>{plan.name}</h3><strong>{plan.price}<small>{plan.name === "Enterprise" ? "" : "/mo"}</small></strong><p>{plan.note}</p><ul>{plan.items.map((item) => <li key={item}><CheckCircle2 size={14} />{item}</li>)}</ul><Link href={plan.name === "Business" || plan.name === "Enterprise" ? "mailto:sales@invoiai.com?subject=InvoiAI%20plan" : "/signup"} className="fresh-text-link">{plan.name === "Business" || plan.name === "Enterprise" ? "Contact sales" : "Start free"}</Link></article>)}</div></section>

    <section id="faq" className="faq-section"><div className="section-heading"><p className="fresh-kicker">FAQ</p><h2>Questions, answered plainly.</h2></div><div className="faq-list">{faqs.map(([question, answer], index) => <article key={question}><button type="button" onClick={() => setOpenFaq(openFaq === index ? null : index)} aria-expanded={openFaq === index}><span>{question}</span><ChevronDown size={18} /></button>{openFaq === index && <p>{answer}</p>}</article>)}</div></section>

    <section id="access" className="access-section"><div><p className="fresh-kicker">Select implementation access</p><h2>Built for teams that want stronger financial habits.</h2><p>Begin with a focused AP workspace, then expand control when your operating rhythm is ready.</p></div><div className="access-card"><span>Most requested</span><h3>AP Control</h3><ul><li>Document intelligence</li><li>Approval authority</li><li>Matching and exception flow</li></ul><Link href={startHref} className="fresh-primary">Request access <ArrowRight size={17} /></Link></div><div className="access-note"><WalletCards size={22} /><p>Implementation access is reviewed for fit, so every team starts with the right control model.</p></div></section>

    <footer id="legal" className="fresh-footer"><Link href="/" className="fresh-brand">invoi<span>ai</span></Link><div className="footer-context"><a href="#features">Platform</a><a href="#workflows">Workflows</a><Link href="/business">Business</Link><Link href="/about">Who we are</Link><a href="#industry">Industry</a><Link href="/docs">Docs</Link><a href="#faq">FAQ</a><a href="#legal">Privacy</a></div><Link href={startHref}>Get started <ArrowRight size={15} /></Link></footer>
  </main>;
}
