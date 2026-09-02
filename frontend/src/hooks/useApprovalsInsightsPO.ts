"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { approvalsApi } from "@/api/approvals";
import { insightsApi } from "@/api/insights";
import { purchaseOrdersApi, type PurchaseOrderFilters } from "@/api/purchase-orders";
import { getErrorMessage } from "@/api/client";
import { useAppStore } from "@/store/useAppStore";

/* ── Approvals ─────────────────────────────────────────────── */

export function usePendingApprovals() {
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return useQuery({
    queryKey: ["approvals-pending", ws],
    queryFn: approvalsApi.listPending,
    enabled: !!ws,
    staleTime: 15_000,
  });
}

export function useOverdueApprovals() {
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return useQuery({
    queryKey: ["approvals-overdue", ws],
    queryFn: approvalsApi.listOverdue,
    enabled: !!ws,
    staleTime: 30_000,
  });
}

export function useDecideApproval() {
  const qc = useQueryClient();
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return useMutation({
    mutationFn: ({ stepId, decision, comment }: { stepId: string; decision: "approved" | "rejected"; comment?: string }) =>
      approvalsApi.decide(stepId, decision, comment),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["approvals-pending", ws] });
      qc.invalidateQueries({ queryKey: ["approvals-overdue", ws] });
      qc.invalidateQueries({ queryKey: ["ap-invoices", ws] });
      qc.invalidateQueries({ queryKey: ["ap-summary", ws] });
      toast.success(vars.decision === "approved" ? "Approved." : "Rejected.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Could not record that decision.")),
  });
}

/* ── Insights ──────────────────────────────────────────────── */

export function useInsights() {
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return useQuery({
    queryKey: ["insights", ws],
    queryFn: insightsApi.list,
    enabled: !!ws,
    staleTime: 60_000,
  });
}

export function useGenerateInsights() {
  const qc = useQueryClient();
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return useMutation({
    mutationFn: insightsApi.generate,
    onSuccess: (fresh) => {
      qc.setQueryData(["insights", ws], fresh);
      toast.success(fresh.length ? `${fresh.length} new insight${fresh.length > 1 ? "s" : ""} found.` : "Nothing new to flag right now.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Could not run the insight scan.")),
  });
}

export function useDismissInsight() {
  const qc = useQueryClient();
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return useMutation({
    mutationFn: insightsApi.dismiss,
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: ["insights", ws] });
      const prev = qc.getQueryData(["insights", ws]);
      qc.setQueryData(["insights", ws], (old: { id: string }[] | undefined) => old?.filter((i) => i.id !== id));
      return { prev };
    },
    onError: (e, _id, ctx) => {
      if (ctx?.prev) qc.setQueryData(["insights", ws], ctx.prev);
      toast.error(getErrorMessage(e, "Could not dismiss that insight."));
    },
  });
}

/* ── Purchase orders ───────────────────────────────────────── */

export function usePurchaseOrders(filters?: PurchaseOrderFilters) {
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return useQuery({
    queryKey: ["purchase-orders", ws, JSON.stringify(filters ?? {})],
    queryFn: () => purchaseOrdersApi.list(filters),
    enabled: !!ws,
    staleTime: 30_000,
  });
}
