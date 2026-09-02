"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { apApi, apDashboardApi, integrationsApi } from "@/api/ap";
import { getErrorMessage } from "@/api/client";
import { useAppStore } from "@/store/useAppStore";

// All AP queries are scoped by workspace id. Switching workspaces never
// clears the cache — it just changes which key each query reads from, so
// data the user already fetched for a workspace stays warm if they switch
// back, and nothing from one workspace can leak into another.
function useWorkspaceKey(...parts: (string | number | undefined | null)[]) {
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return { key: [...parts, ws] as const, enabled: !!ws, ws };
}

export function useChartOfAccounts() {
  const { key, enabled } = useWorkspaceKey("chart-of-accounts");
  return useQuery({ queryKey: key, queryFn: apApi.listChartOfAccounts, enabled, staleTime: 5 * 60_000 });
}

export function useSyncChartOfAccounts() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: apApi.syncChartOfAccounts,
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["chart-of-accounts", ws] });
      toast.success(`${result?.synced ?? "Chart of Accounts"} synced from QuickBooks.`);
    },
    onError: (e) => toast.error(getErrorMessage(e, "QuickBooks account sync failed.")),
  });
}

export function useAPExceptions() {
  const { key, enabled } = useWorkspaceKey("ap-exceptions");
  return useQuery({ queryKey: key, queryFn: apApi.listExceptions, enabled, staleTime: 20_000 });
}

export function useAPStatus(documentId: string | null) {
  const { key, enabled } = useWorkspaceKey("ap-status", documentId ?? undefined);
  return useQuery({
    queryKey: key,
    queryFn: () => apApi.getStatus(documentId!),
    enabled: enabled && !!documentId,
    staleTime: 2_000,
    refetchInterval: (q) => {
      const status = q.state.data?.ap_status;
      return status && !["approved", "rejected", "payment_ready", "paid", "reconciled"].includes(status) ? 3000 : false;
    },
  });
}

export function useDocumentCodings(documentId: string | null) {
  const { key, enabled } = useWorkspaceKey("ap-codings", documentId ?? undefined);
  return useQuery({ queryKey: key, queryFn: () => apApi.getCodings(documentId!), enabled: enabled && !!documentId, staleTime: 10_000 });
}

export function useApproveCodings() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: apApi.approveCodings,
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ["ap-codings", id, ws] });
      qc.invalidateQueries({ queryKey: ["ap-status", id, ws] });
      qc.invalidateQueries({ queryKey: ["ap-invoices", ws] });
      qc.invalidateQueries({ queryKey: ["ap-summary", ws] });
      toast.success("Coding approved and routed to approval.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Coding approval failed.")),
  });
}

export function useIntegrations() {
  const { key, enabled } = useWorkspaceKey("integrations");
  return useQuery({ queryKey: key, queryFn: integrationsApi.list, enabled, staleTime: 30_000 });
}

/* ── AP dashboard: summary, trends, invoices, aging, vendor statements ── */

export function useAPSummary(filters?: apDashboardApi.SummaryFilters) {
  const { key, enabled } = useWorkspaceKey("ap-summary", JSON.stringify(filters ?? {}));
  return useQuery({
    queryKey: key,
    queryFn: () => apDashboardApi.getSummary(filters),
    enabled,
    staleTime: 30_000,
  });
}

export function useAPInvoices(filters?: apDashboardApi.InvoiceFilters) {
  const { key, enabled } = useWorkspaceKey("ap-invoices", JSON.stringify(filters ?? {}));
  return useQuery({
    queryKey: key,
    queryFn: () => apDashboardApi.listInvoices(filters),
    enabled,
    staleTime: 15_000,
  });
}

export function useAPAging(filters?: apDashboardApi.SummaryFilters) {
  const { key, enabled } = useWorkspaceKey("ap-aging", JSON.stringify(filters ?? {}));
  return useQuery({ queryKey: key, queryFn: () => apDashboardApi.getAging(filters), enabled, staleTime: 60_000 });
}

export function useTopVendors(filters?: apDashboardApi.SummaryFilters) {
  const { key, enabled } = useWorkspaceKey("ap-top-vendors", JSON.stringify(filters ?? {}));
  return useQuery({ queryKey: key, queryFn: () => apDashboardApi.getTopVendors(filters), enabled, staleTime: 60_000 });
}

export function useVendorStatement(vendorId: string | null) {
  const { key, enabled } = useWorkspaceKey("vendor-statement", vendorId ?? undefined);
  return useQuery({
    queryKey: key,
    queryFn: () => apDashboardApi.getVendorStatement(vendorId!),
    enabled: enabled && !!vendorId,
    staleTime: 30_000,
  });
}

export function useVendorsList(filters?: { search?: string; risk_level?: string }) {
  const { key, enabled } = useWorkspaceKey("vendors-list", JSON.stringify(filters ?? {}));
  return useQuery({ queryKey: key, queryFn: () => apDashboardApi.listVendors(filters), enabled, staleTime: 30_000 });
}
