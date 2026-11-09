"use client";

import { Check, Loader2, AlertTriangle, Circle } from "lucide-react";

const STEPS = [
  { key: "reading", title: "Reading document", text: "Checking the file structure and preparing the document." },
  { key: "ocr", title: "Extracting information", text: "Reading text, tables, and important document details." },
  { key: "classification", title: "Identifying document type", text: "Determining what this document is and which financial workflow applies." },
  { key: "analysis", title: "Analyzing financial data", text: "Understanding the extracted data before running deeper checks." },
  { key: "validation", title: "Validating extracted data", text: "Checking dates, amounts, totals, and financial consistency." },
  { key: "ocr_check", title: "Checking OCR quality", text: "Checking extraction confidence and document readability." },
  { key: "math_check", title: "Checking calculations", text: "Checking totals, taxes, line items, dates, and financial consistency." },
  { key: "vendor_check", title: "Checking vendor history", text: "Comparing this vendor with its previous financial activity." },
  { key: "duplicate_check", title: "Checking for duplicates", text: "Looking for duplicate or highly similar documents." },
  { key: "historical_check", title: "Comparing historical patterns", text: "Looking for unusual changes compared with normal vendor behavior." },
  { key: "purchase_order_check", title: "Checking related records", text: "Checking available purchase-order information." },
  { key: "fraud_check", title: "Running risk & fraud checks", text: "Looking for suspicious signals, anomalies, and unusual behavior." },
  { key: "compliance_check", title: "Checking compliance", text: "Checking policy and compliance signals." },
  { key: "embedding", title: "Building financial memory", text: "Making this document searchable and useful for future InvoiAI insights." },
  { key: "complete", title: "Analysis complete", text: "InvoiAI has finished checking this document." },
];

function indexFor(key?: string) {
  const i = STEPS.findIndex((s) => s.key === key);
  return i < 0 ? 0 : i;
}

export default function DocumentProcessingTimeline({
  step,
  message,
  progress = 0,
  failed = false,
}: {
  step?: string;
  message?: string;
  progress?: number;
  failed?: boolean;
}) {
  const current = indexFor(step);
  const safeProgress = Math.min(100, Math.max(0, Number(progress) || 0));

  return (
    <div className="doc-processing-card" style={{ minWidth: 0, width: "100%", maxWidth: "100%" }}>
      <div className="doc-processing-head">
        <div>
          <div className="section-label">INVOIAI INTELLIGENCE</div>
          <h2 className="serif doc-processing-title">
            {failed ? "Processing stopped" : STEPS[current]?.title || "Processing document"}
          </h2>
          <p className="doc-processing-message">
            {message || (failed ? "The document needs attention before processing can continue." : STEPS[current]?.text)}
          </p>
        </div>
        <div className="doc-processing-percent">{safeProgress}%</div>
      </div>

      <div className="doc-progress-track">
        <div className="doc-progress-fill" style={{ width: `${safeProgress}%` }} />
      </div>

      <div className="doc-processing-steps">
        {STEPS.map((item, i) => {
          const done = !failed && i < current;
          const active = i === current;
          const complete = item.key === "complete" && step === "complete";
          const failedHere = failed && active;

          return (
            <div key={item.key} className={`doc-processing-step ${done || complete ? "done" : ""} ${active && !failed ? "active" : ""} ${failedHere ? "failed" : ""}`}>
              <div className="doc-processing-icon">
                {done || complete ? <Check size={13} /> : failedHere ? <AlertTriangle size={13} /> : active ? <Loader2 size={13} className="animate-spin" /> : <Circle size={8} />}
              </div>
              <div>
                <div className="doc-processing-step-title">{item.title}</div>
                {(active || done) && <div className="doc-processing-step-text">{item.text}</div>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
