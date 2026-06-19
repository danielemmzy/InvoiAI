"use client";
// useBilling.ts — Stripe subscription hook

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { billingApi } from "@/api/billing";

export function useBilling() {
  const queryClient = useQueryClient();

  // Fetch current plan + usage + subscription details
  const { data: billing, isLoading } = useQuery({
    queryKey: ["billing"],
    queryFn: billingApi.getSubscription,
    staleTime: 5 * 60 * 1000,
  });

  // Start Stripe checkout — redirects to Stripe hosted page
  const checkoutMutation = useMutation({
    mutationFn: (plan: "starter" | "pro") =>
      billingApi.createCheckout(
        plan,
        `${window.location.origin}/dashboard/billing?success=true`,
        `${window.location.origin}/dashboard/billing?cancelled=true`
      ),
    onSuccess: (data) => {
      // Redirect browser to Stripe checkout page
      window.location.href = data.checkout_url;
    },
    onError: () =>
      toast.error("Could not start checkout. Please try again."),
  });

  // Cancel subscription at period end
  const cancelMutation = useMutation({
    mutationFn: billingApi.cancelSubscription,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["billing"] });
      queryClient.invalidateQueries({ queryKey: ["me"] });
      toast.success(data.message);
    },
    onError: () =>
      toast.error("Failed to cancel subscription. Please try again."),
  });

  return {
    billing,
    isLoading,

    startCheckout: (plan: "starter" | "pro") =>
      checkoutMutation.mutate(plan),
    isCheckingOut: checkoutMutation.isPending,

    cancelSubscription: () => cancelMutation.mutate(),
    isCancelling: cancelMutation.isPending,
  };
}