"use client";
// useBilling.ts — Stripe subscription hook

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { billingApi } from "@/api/billing";
import { useAppStore } from "@/store/useAppStore";

export function usePlanCatalog() {
  return useQuery({
    queryKey: ["plan-catalog"],
    queryFn: billingApi.listPlans,
    staleTime: 10 * 60_000, // pricing doesn't change minute to minute
  });
}

export function useBilling() {
  const queryClient = useQueryClient();
  const ws = useAppStore((s) => s.activeWorkspace?.id);

  // Fetch current plan + usage + subscription details
  const { data: billing, isLoading, isError, refetch } = useQuery({
    queryKey: ["billing", ws],
    queryFn: billingApi.getSubscription,
    enabled: !!ws,
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

  // Start Stripe checkout — redirects to Stripe hosted page
  const checkoutMutation = useMutation({
    mutationFn: ({ plan, annual }: { plan: "starter" | "pro" | "business"; annual: boolean }) =>
      billingApi.createCheckout(
        plan,
        `${window.location.origin}/dashboard/billing?success=true`,
        `${window.location.origin}/dashboard/billing?cancelled=true`,
        annual
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
      queryClient.invalidateQueries({ queryKey: ["billing", ws] });
      queryClient.invalidateQueries({ queryKey: ["me"] });
      toast.success(data.message);
    },
    onError: () =>
      toast.error("Failed to cancel subscription. Please try again."),
  });

  return {
    billing,
    isLoading,
    isError,
    refetch,

    startCheckout: (plan: "starter" | "pro" | "business", annual = false) =>
      checkoutMutation.mutate({ plan, annual }),
    isCheckingOut: checkoutMutation.isPending,

    cancelSubscription: () => cancelMutation.mutate(),
    isCancelling: cancelMutation.isPending,
  };
}