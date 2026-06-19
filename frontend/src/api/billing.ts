// ─────────────────────────────────────────────
// Billing API — Stripe checkout + subscription
// ─────────────────────────────────────────────

import client from "./client";
import { BillingInfo, CheckoutResponse } from "@/types";

export const billingApi = {
  // Create Stripe checkout session — returns URL to redirect to
  createCheckout: async (
    plan: "starter" | "pro",
    successUrl: string,
    cancelUrl: string
  ): Promise<CheckoutResponse> => {
    const { data } = await client.post<CheckoutResponse>("/billing/checkout", {
      plan,
      success_url: successUrl,
      cancel_url: cancelUrl,
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
};