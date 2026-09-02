// ─────────────────────────────────────────────
// Billing API — Stripe checkout + subscription
// ─────────────────────────────────────────────

import { client } from "./client";
import { BillingInfo, CheckoutResponse } from "@/types";

export interface PlanCatalogEntry {
  id: "free" | "starter" | "pro" | "business" | "enterprise";
  display_name: string;
  price_monthly: number;
  price_annual_monthly: number;
  contact_sales: boolean;
  seats: number | "Unlimited";
  monthly_documents: number | "Unlimited";
  max_accounting_integrations: number;
  max_matching_ways: number;
  max_business_workspaces: number | "Unlimited";
  export_formats: string[];
  features: string[];
}

export const billingApi = {
  // Create Stripe checkout session — returns URL to redirect to
  createCheckout: async (
    plan: "starter" | "pro" | "business",
    successUrl: string,
    cancelUrl: string,
    annual = false
  ): Promise<CheckoutResponse> => {
    const { data } = await client.post<CheckoutResponse>("/billing/checkout", {
      plan,
      success_url: successUrl,
      cancel_url: cancelUrl,
      annual,
    });
    return data;
  },

  // Get current subscription + usage
  getSubscription: async (): Promise<BillingInfo> => {
    const { data } = await client.get<BillingInfo>("/billing/subscription");
    return data;
  },

  // Cancel at period end
  cancelSubscription: async (): Promise<{ message: string }> => {
    const { data } = await client.post<{ message: string }>("/billing/cancel");
    return data;
  },

  // Public plan catalog — single source of truth, backed by core/plan.py.
  // No auth required; this is what both the marketing pricing page and
  // the in-app upgrade screen should read from instead of hardcoding
  // numbers that can drift from what Stripe actually charges.
  listPlans: async (): Promise<PlanCatalogEntry[]> => {
    const { data } = await client.get<PlanCatalogEntry[]>("/billing/plans");
    return data;
  },
};