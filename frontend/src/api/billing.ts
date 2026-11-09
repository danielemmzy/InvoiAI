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

  // Maximum number of files allowed in ONE upload request.
  // Backend values:
  // Free       = 3
  // Starter    = 10
  // Pro        = 25
  // Business   = 50
  // Enterprise = 100
  max_batch_upload: number;

  max_accounting_integrations: number;
  max_matching_ways: number;

  max_business_workspaces: number | "Unlimited";

  export_formats: string[];

  features: string[];
}

type PlanCatalogEnvelope =
  | PlanCatalogEntry[]
  | { data?: PlanCatalogEntry[] | { plans?: PlanCatalogEntry[] }; plans?: PlanCatalogEntry[] };

/**
 * The public plan endpoint has historically been served both as a bare array
 * and behind API envelopes. Normalise it once at the boundary so screens never
 * call Array.prototype methods on an unexpected response object.
 */
export function normalizePlanCatalog(payload: unknown): PlanCatalogEntry[] {
  if (Array.isArray(payload)) return payload as PlanCatalogEntry[];

  if (payload && typeof payload === "object") {
    const envelope = payload as Exclude<PlanCatalogEnvelope, PlanCatalogEntry[]>;
    if (Array.isArray(envelope.plans)) return envelope.plans;
    if (Array.isArray(envelope.data)) return envelope.data;
    if (envelope.data && typeof envelope.data === "object" && Array.isArray(envelope.data.plans)) {
      return envelope.data.plans;
    }
  }

  throw new TypeError("The plans response has an unsupported format.");
}

export const billingApi = {
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

  getSubscription: async (): Promise<BillingInfo> => {
    const { data } = await client.get<BillingInfo>("/billing/subscription");
    return data;
  },

  cancelSubscription: async (): Promise<{ message: string }> => {
    const { data } = await client.post<{ message: string }>("/billing/cancel");
    return data;
  },

  listPlans: async (): Promise<PlanCatalogEntry[]> => {
    const { data } = await client.get<unknown>("/billing/plans");
    return normalizePlanCatalog(data);
  },
};
