"use client";
// Billing page — /dashboard/billing

import { useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { Check, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useBilling } from "@/hooks/useBilling";
import { useAppStore } from "@/store/useAppStore";

const PLANS = [
  {
    id: "free" as const,
    label: "Free",
    price: "$0",
    period: "forever",
    features: ["10 documents / month", "Excel & CSV export", "20 industries", "Basic history"],
    featured: false,
  },
  {
    id: "starter" as const,
    label: "Starter",
    price: "$12",
    period: "per month",
    features: ["100 documents / month", "Google Sheets export", "Priority extraction", "Full history"],
    featured: true,
  },
  {
    id: "pro" as const,
    label: "Pro",
    price: "$29",
    period: "per month",
    features: ["500 documents / month", "API access", "All export formats", "Usage analytics"],
    featured: false,
  },
];

export default function BillingPage() {
  const searchParams = useSearchParams();
  const { user } = useAppStore();
  const { billing, isLoading, startCheckout, isCheckingOut, cancelSubscription, isCancelling } = useBilling();
  const currentPlan = user?.plan || "free";

  useEffect(() => {
    if (searchParams?.get("success") === "true") {
      toast.success("Payment successful! Your plan has been upgraded.");
    }
    if (searchParams?.get("cancelled") === "true") {
      toast.error("Payment cancelled.");
    }
  }, [searchParams]);

  return (
    <DashboardLayout>
      <div className="dash-page-header">
        <div className="section-label">§03 Account / Billing</div>
        <div className="dash-title serif">Billing & Plans</div>
        <div className="dash-subtitle">Manage your subscription and usage limits.</div>
      </div>

      {/* Current usage */}
      {billing && (
        <div className="card" style={{ marginBottom: 28 }}>
          <div className="card-header">
            <span className="card-title">Current usage — {billing.usage?.month}</span>
          </div>
          <div className="billing-usage">
            <div className="billing-usage-row">
              <div>
                <div className="billing-used serif">{billing.usage?.used}</div>
                <div className="billing-used-label">
                  of {billing.usage?.limit} documents used
                </div>
              </div>
              <div style={{ flex: 1 }}>
                <div className="usage-bar-wrap">
                  <div
                    className={`usage-bar${billing.usage?.limit_reached ? " danger" : ""}`}
                    style={{
                      width: `${Math.min(
                        ((billing.usage?.used || 0) / (billing.usage?.limit || 1)) * 100,
                        100
                      )}%`,
                    }}
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
      )}

      {/* Plans */}
      <div className="pricing-grid">
        {PLANS.map((plan) => {
          const isCurrent = currentPlan === plan.id;
          return (
            <div key={plan.id} className={`pricing-card${plan.featured ? " featured" : ""}`}>
              <div className="pricing-plan">
                {plan.label}
                {isCurrent && (
                  <span style={{ marginLeft: 8, fontSize: 9, padding: "2px 6px", background: "#C8922A", color: "#FFF", borderRadius: 3 }}>
                    CURRENT
                  </span>
                )}
              </div>
              <div className="pricing-price serif">{plan.price}</div>
              <div className="pricing-period">{plan.period}</div>

              {plan.features.map((f) => (
                <div key={f} className="pricing-feature">{f}</div>
              ))}

              <div style={{ marginTop: "auto", paddingTop: 24 }}>
                {isCurrent ? (
                  <div className="pricing-current">Current plan</div>
                ) : plan.id === "free" ? (
                  <div className="pricing-current">—</div>
                ) : (
                  <button
                    onClick={() => startCheckout(plan.id)}
                    disabled={isCheckingOut}
                    className="pricing-btn"
                    style={{ width: "100%" }}
                  >
                    {isCheckingOut
                      ? <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                          <Loader2 size={14} className="animate-spin" /> Redirecting...
                        </span>
                      : `Upgrade to ${plan.label} →`
                    }
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </DashboardLayout>
  );
}