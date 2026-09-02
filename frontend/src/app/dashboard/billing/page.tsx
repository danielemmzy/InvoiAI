"use client";

// Billing page — /dashboard/billing
// Plan cards are rendered from GET /billing/plans (core/plan.py), not
// hardcoded here — the numbers can never drift from what checkout
// actually charges.

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2, Check, ShieldCheck } from "lucide-react";
import toast from "react-hot-toast";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError } from "@/components/ui/PageState";
import { useBilling, usePlanCatalog } from "@/hooks/useBilling";
import { useAppStore } from "@/store/useAppStore";
import { useQueryClient } from "@tanstack/react-query";
import type { PlanCatalogEntry } from "@/api/billing";

// Curated marketing copy per tier — the numbers (price, seats, document
// limit, integrations, matching, exports) all come from the live catalog
// above; this is just the qualitative bullet list, kept in the order the
// pricing model was designed around.
const PLAN_HIGHLIGHTS: Record<string, string[]> = {
  free: [
    "OCR + AI extraction",
    "Basic verification (8 modules)",
    "2-way PO matching",
    "1 approval workflow",
    "Rule-based coding only",
  ],
  starter: [
    "AI GL coding",
    "Exception queue",
    "Bill push to QuickBooks/Xero",
    "Insights feed",
    "Finance Copilot",
    "Personal workspace, fully unlocked",
  ],
  pro: [
    "Everything in Starter",
    "3-way matching (PO + goods receipt)",
    "Email invoice intake",
    "Vendor analytics + cash flow",
    "Tolerance engine",
    "Vendor bank-change controls",
    "Audit trail",
  ],
  business: [
    "Everything in Pro",
    "Unlimited seats",
    "Multi-org / subsidiaries",
    "Department budget controls",
    "Segregation of duties",
    "Custom coding rules",
    "Weekly AI digest",
    "Priority support + guided onboarding",
  ],
  enterprise: [
    "Everything in Business",
    "SSO / SAML",
    "Custom ERP integrations",
    "Dedicated SLA",
    "Custom contract",
    "Data residency",
  ],
};

function formatDocs(v: number | "Unlimited") {
  return v === "Unlimited" ? "Unlimited documents / month" : `${v} documents / month`;
}
function formatSeats(v: number | "Unlimited") {
  return v === "Unlimited" ? "Unlimited seats" : `${v} seat${v === 1 ? "" : "s"}`;
}

function BillingContent() {
  const searchParams = useSearchParams();
  const { user } = useAppStore();
  const [annual, setAnnual] = useState(false);

  const {
    billing, isLoading: billingLoading, isError: billingError, refetch: refetchBilling,
    startCheckout, isCheckingOut, cancelSubscription, isCancelling,
  } = useBilling();
  const { data: plans, isLoading: plansLoading, isError: plansError, refetch: refetchPlans } = usePlanCatalog();

  const currentPlan = user?.plan || "free";
  const queryClient = useQueryClient();

  useEffect(() => {
    if (searchParams?.get("success") === "true") {
      const timer = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["me"] });
        queryClient.invalidateQueries({ queryKey: ["billing"] });
      }, 2000);
      toast.success("Payment successful! Your plan has been upgraded.");
      return () => clearTimeout(timer);
    }
    if (searchParams?.get("cancelled") === "true") {
      toast.error("Payment cancelled.");
    }
  }, [searchParams, queryClient]);

  return (
    <DashboardLayout>
      <div className="dash-page-header">
        <div className="section-label">§03 Account / Billing</div>
        <div className="dash-title serif">Billing & Plans</div>
        <div className="dash-subtitle">Manage your subscription and usage limits.</div>
      </div>

      {billingLoading ? (
        <PageLoading variant="cards" cards={1} />
      ) : billingError ? (
        <PageError title="Couldn't load your usage" onRetry={refetchBilling} compact />
      ) : billing ? (
        <div className="card" style={{ marginBottom: 28 }}>
          <div className="card-header">
            <span className="card-title">Current usage — {billing.usage?.month}</span>
          </div>

          <div className="billing-usage">
            <div className="billing-usage-row">
              <div>
                <div className="billing-used serif">{billing.usage?.used}</div>
                <div className="billing-used-label">of {billing.usage?.limit} documents used</div>
              </div>

              <div style={{ flex: 1 }}>
                <div className="usage-bar-wrap">
                  <div
                    className={`usage-bar${billing.usage?.limit_reached ? " danger" : ""}`}
                    style={{ width: `${Math.min(((billing.usage?.used || 0) / (billing.usage?.limit || 1)) * 100, 100)}%` }}
                  />
                </div>
              </div>

              <div style={{ fontSize: 13, fontWeight: 500, color: "#1A1916", minWidth: 60, textAlign: "right" }}>
                {billing.usage?.remaining} left
              </div>
            </div>

            {billing.subscription?.cancel_at_period_end && (
              <div style={{ fontSize: 12, color: "#C8922A", marginTop: 8 }}>
                ⚠ Subscription cancels at end of billing period. You keep access until then.
              </div>
            )}

            {billing.subscription?.status === "active" && !billing.subscription.cancel_at_period_end && currentPlan !== "free" && (
              <button
                onClick={() => {
                  if (confirm("Cancel your subscription? You keep access until the end of your billing period.")) {
                    cancelSubscription();
                  }
                }}
                disabled={isCancelling}
                style={{ marginTop: 12, fontSize: 12, color: "#E57373", background: "none", border: "none", cursor: "pointer", fontFamily: "'DM Sans', sans-serif" }}
              >
                {isCancelling ? "Cancelling..." : "Cancel subscription"}
              </button>
            )}
          </div>
        </div>
      ) : null}

      <div style={{ display: "flex", justifyContent: "center" }}>
        <div className="pricing-toggle">
          <button type="button" className={`pricing-toggle-btn${!annual ? " active" : ""}`} onClick={() => setAnnual(false)}>Monthly</button>
          <button type="button" className={`pricing-toggle-btn${annual ? " active" : ""}`} onClick={() => setAnnual(true)}>
            Annual <span className="pricing-toggle-save">Save ~18%</span>
          </button>
        </div>
      </div>

      {plansLoading ? (
        <PageLoading variant="cards" cards={5} />
      ) : plansError ? (
        <PageError title="Couldn't load the plan catalog" onRetry={refetchPlans} />
      ) : (
        <div className="pricing-grid tiers-5" style={{ marginTop: 20 }}>
          {(plans || []).map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              annual={annual}
              isCurrent={currentPlan === plan.id}
              isCheckingOut={isCheckingOut}
              onUpgrade={() => startCheckout(plan.id as "starter" | "pro" | "business", annual)}
            />
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}

function PlanCard({
  plan, annual, isCurrent, isCheckingOut, onUpgrade,
}: {
  plan: PlanCatalogEntry;
  annual: boolean;
  isCurrent: boolean;
  isCheckingOut: boolean;
  onUpgrade: () => void;
}) {
  const featured = plan.id === "pro";
  const price = annual ? plan.price_annual_monthly : plan.price_monthly;
  const highlights = PLAN_HIGHLIGHTS[plan.id] || [];

  return (
    <div className={`pricing-card${featured ? " featured" : ""}`}>
      <div className="pricing-plan">
        {plan.display_name}
        {isCurrent && <span className="pricing-card-badge">Current</span>}
      </div>

      {plan.contact_sales ? (
        <div className="pricing-contact-price">Contact us</div>
      ) : (
        <div className="pricing-price-row">
          <div className="pricing-price serif">${price}</div>
          {annual && price !== plan.price_monthly && (
            <span className="pricing-price-was">${plan.price_monthly}</span>
          )}
        </div>
      )}
      <div className="pricing-period">
        {plan.contact_sales ? "custom contract" : plan.price_monthly === 0 ? "forever" : annual ? "per month, billed annually" : "per month"}
      </div>

      <div className="pricing-feature">{formatDocs(plan.monthly_documents)}</div>
      <div className="pricing-feature">{formatSeats(plan.seats)}</div>
      <div className="pricing-feature">
        {plan.max_accounting_integrations >= 5 ? "QuickBooks + Xero + more" : plan.max_accounting_integrations > 1 ? "QuickBooks + Xero" : "QuickBooks or Xero"}
      </div>
      <div className="pricing-feature">{plan.max_matching_ways === 3 ? "2 & 3-way matching" : "2-way matching"}</div>
      {highlights.map((h) => (
        <div key={h} className="pricing-feature">{h}</div>
      ))}

      <div style={{ marginTop: "auto", paddingTop: 24 }}>
        {isCurrent ? (
          <div className="pricing-current"><ShieldCheck size={13} style={{ verticalAlign: -2, marginRight: 4 }} />Current plan</div>
        ) : plan.contact_sales ? (
          <a href="mailto:sales@invoiai.com?subject=Enterprise%20plan" className="pricing-btn" style={{ display: "block", textAlign: "center", textDecoration: "none" }}>
            Contact sales
          </a>
        ) : plan.id === "free" ? (
          <div className="pricing-current">—</div>
        ) : (
          <button onClick={onUpgrade} disabled={isCheckingOut} className="pricing-btn" style={{ width: "100%" }}>
            {isCheckingOut ? (
              <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                <Loader2 size={14} className="animate-spin" /> Redirecting...
              </span>
            ) : (
              `Upgrade to ${plan.display_name} →`
            )}
          </button>
        )}
      </div>
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense
      fallback={
        <DashboardLayout>
          <PageLoading />
        </DashboardLayout>
      }
    >
      <BillingContent />
    </Suspense>
  );
}
