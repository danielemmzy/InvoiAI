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
  return useQuery({ queryKey: key, queryFn: () => apApi.listChartOfAccounts(), enabled, staleTime: 5 * 60_000 });
}

export function useSyncChartOfAccounts() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: apApi.syncChartOfAccounts,
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["chart-of-accounts", ws] });
      toast.success(`Chart of Accounts synced from ${result?.provider ?? "the active accounting provider"}.`);
    },
    onError: (e) => toast.error(getErrorMessage(e, "Chart of Accounts sync failed.")),
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

export function useSyncSuppliers() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: integrationsApi.syncSuppliers,
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["integrations", ws] });
      toast.success(`Suppliers: ${result.imported} added, ${result.updated} updated, ${result.failed} failed.`);
    },
    onError: (e) => toast.error(getErrorMessage(e, "Supplier import failed.")),
  });
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

/* ════════════════════════════════════════════════════════════
   AP Workflow Engine — routing rules, approval groups, payment
   queue/authorization, payment instructions, invoice comments,
   vendor W-9/bank-change controls, member approval limits.
   ════════════════════════════════════════════════════════════ */

import {
  apRulesApi, apGroupsApi, paymentAuthorizationApi, invoiceCommentsApi,
  memberApprovalLimitsApi, paymentInstructionsApi, vendorControlsApi,
  type ApprovalRuleScope, type ApprovalRuleCreate, type ApprovalRuleUpdate,
  type MemberApprovalLimits, type VendorDocumentRequestType,
} from "@/api/ap";
import { membersApi } from "@/api/members";

export function useOrgMembers() {
  const { key, enabled } = useWorkspaceKey("org-members");
  return useQuery({ queryKey: key, queryFn: membersApi.list, enabled, staleTime: 30_000 });
}

export function useApprovalRules(scope?: ApprovalRuleScope) {
  const { key, enabled } = useWorkspaceKey("ap-rules", scope);
  return useQuery({ queryKey: key, queryFn: () => apRulesApi.list(scope), enabled, staleTime: 30_000 });
}

export function useCreateApprovalRule() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: (payload: ApprovalRuleCreate) => apRulesApi.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ap-rules", undefined, ws] });
      qc.invalidateQueries({ queryKey: ["ap-rules", "bill", ws] });
      qc.invalidateQueries({ queryKey: ["ap-rules", "payment", ws] });
      toast.success("Approval rule created.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to create approval rule.")),
  });
}

export function useUpdateApprovalRule() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({ ruleId, payload }: { ruleId: string; payload: ApprovalRuleUpdate }) => apRulesApi.update(ruleId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ap-rules", undefined, ws] });
      toast.success("Approval rule updated.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to update approval rule.")),
  });
}

export function useDeleteApprovalRule() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: (ruleId: string) => apRulesApi.remove(ruleId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ap-rules", undefined, ws] });
      toast.success("Approval rule deleted.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to delete approval rule.")),
  });
}

export function useApprovalGroups() {
  const { key, enabled } = useWorkspaceKey("ap-groups");
  return useQuery({ queryKey: key, queryFn: apGroupsApi.list, enabled, staleTime: 30_000 });
}

export function useCreateApprovalGroup() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) => apGroupsApi.create(name, description),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ap-groups", ws] }); toast.success("Group created."); },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to create group.")),
  });
}

export function useGroupMembers(groupId: string | null) {
  const { key, enabled } = useWorkspaceKey("ap-group-members", groupId ?? undefined);
  return useQuery({
    queryKey: key,
    queryFn: () => apGroupsApi.listMembers(groupId!),
    enabled: enabled && !!groupId,
    staleTime: 30_000,
  });
}

export function useAddGroupMember() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({ groupId, userId }: { groupId: string; userId: string }) => apGroupsApi.addMember(groupId, userId),
    onSuccess: (_r, { groupId }) => {
      qc.invalidateQueries({ queryKey: ["ap-group-members", groupId, ws] });
      toast.success("Member added.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to add member.")),
  });
}

export function useRemoveGroupMember() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({ groupId, userId }: { groupId: string; userId: string }) => apGroupsApi.removeMember(groupId, userId),
    onSuccess: (_r, { groupId }) => {
      qc.invalidateQueries({ queryKey: ["ap-group-members", groupId, ws] });
      toast.success("Member removed.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to remove member.")),
  });
}

export function useClaimApprovalStep() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: (stepId: string) => apGroupsApi.claimStep(stepId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["approvals-queue", ws] });
      toast.success("Task claimed — it's yours to decide.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to claim this task — someone may have already claimed it.")),
  });
}

export function usePaymentQueue() {
  const { key, enabled } = useWorkspaceKey("payment-queue");
  return useQuery({ queryKey: key, queryFn: paymentAuthorizationApi.getQueue, enabled, staleTime: 15_000 });
}

export function useEvaluatePaymentAuthorization() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: (documentId: string) => paymentAuthorizationApi.evaluate(documentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["payment-queue", ws] }),
    onError: (e) => toast.error(getErrorMessage(e, "Failed to re-evaluate payment authorization.")),
  });
}

export function useOverridePaymentBlock() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({ documentId, reason }: { documentId: string; reason: string }) => paymentAuthorizationApi.override(documentId, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payment-queue", ws] });
      toast.success("Payment override recorded — the payment has been released.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Override failed.")),
  });
}

export function usePaymentInstructions(documentId: string | null) {
  const { key, enabled } = useWorkspaceKey("payment-instructions", documentId ?? undefined);
  return useQuery({
    queryKey: key,
    queryFn: () => paymentInstructionsApi.listForDocument(documentId!),
    enabled: enabled && !!documentId,
    staleTime: 15_000,
  });
}

export function usePaymentInstructionEvents(instructionId: string | null) {
  const { key, enabled } = useWorkspaceKey("payment-instruction-events", instructionId ?? undefined);
  return useQuery({
    queryKey: key,
    queryFn: () => paymentInstructionsApi.listEvents(instructionId!),
    enabled: enabled && !!instructionId,
    staleTime: 10_000,
  });
}

export function useScheduleDocumentPayment() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({
      documentId,
      ...input
    }: {
      documentId: string;
      payment_method?: string | null;
      scheduled_date?: string | null;
      idempotency_key?: string | null;
    }) => paymentInstructionsApi.create(documentId, input),
    onSuccess: (_r, { documentId }) => {
      qc.invalidateQueries({ queryKey: ["payment-instructions", documentId, ws] });
      qc.invalidateQueries({ queryKey: ["payment-queue", ws] });
      toast.success("Payment approval workflow started.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to schedule payment.")),
  });
}

export function useCancelPaymentInstruction(documentId: string) {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({ instructionId, reason }: { instructionId: string; reason: string }) =>
      paymentInstructionsApi.cancel(instructionId, reason),
    onSuccess: (_r, { instructionId }) => {
      qc.invalidateQueries({ queryKey: ["payment-instructions", documentId, ws] });
      qc.invalidateQueries({ queryKey: ["payment-instruction-events", instructionId, ws] });
      qc.invalidateQueries({ queryKey: ["payment-queue", ws] });
      toast.success("Payment instruction cancelled.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Could not cancel the payment instruction.")),
  });
}

export function useReconcilePaymentInstruction(documentId: string) {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: (instructionId: string) => paymentInstructionsApi.reconcile(instructionId),
    onSuccess: (_r, instructionId) => {
      qc.invalidateQueries({ queryKey: ["payment-instructions", documentId, ws] });
      qc.invalidateQueries({ queryKey: ["payment-instruction-events", instructionId, ws] });
      qc.invalidateQueries({ queryKey: ["payment-queue", ws] });
      toast.success("Provider status checked and reconciled.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Could not reconcile the payment instruction.")),
  });
}

export function useInvoiceComments(documentId: string | null) {
  const { key, enabled } = useWorkspaceKey("invoice-comments", documentId ?? undefined);
  return useQuery({
    queryKey: key,
    queryFn: () => invoiceCommentsApi.list(documentId!),
    enabled: enabled && !!documentId,
    staleTime: 10_000,
  });
}

export function useAddInvoiceComment() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({ documentId, body, mentionedUserIds }: { documentId: string; body: string; mentionedUserIds?: string[] }) =>
      invoiceCommentsApi.add(documentId, body, mentionedUserIds),
    onSuccess: (_r, { documentId }) => qc.invalidateQueries({ queryKey: ["invoice-comments", documentId, ws] }),
    onError: (e) => toast.error(getErrorMessage(e, "Failed to post comment.")),
  });
}

export function useVendorDocumentRequests(vendorId: string | null) {
  const { key, enabled } = useWorkspaceKey("vendor-document-requests", vendorId ?? undefined);
  return useQuery({
    queryKey: key,
    queryFn: () => vendorControlsApi.listRequests(vendorId!),
    enabled: enabled && !!vendorId,
    staleTime: 20_000,
  });
}

export function useRequestVendorDocument() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({ vendorId, requestType }: { vendorId: string; requestType: VendorDocumentRequestType }) =>
      vendorControlsApi.requestDocument(vendorId, requestType),
    onSuccess: (_r, { vendorId }) => {
      qc.invalidateQueries({ queryKey: ["vendor-document-requests", vendorId, ws] });
      toast.success("Request sent to vendor.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to send request.")),
  });
}

export function useVerifyBankChange() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({ requestId, approve, reason }: { requestId: string; approve: boolean; reason?: string }) =>
      vendorControlsApi.verifyBankChange(requestId, approve, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vendor-document-requests"] });
      toast.success("Bank-change decision recorded.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to record decision.")),
  });
}

export function useSetMemberApprovalLimits() {
  const qc = useQueryClient();
  const { ws } = useWorkspaceKey();
  return useMutation({
    mutationFn: ({ membershipId, payload }: { membershipId: string; payload: MemberApprovalLimits }) =>
      memberApprovalLimitsApi.set(membershipId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["org-members", ws] });
      toast.success("Approval limits updated.");
    },
    onError: (e) => toast.error(getErrorMessage(e, "Failed to update approval limits.")),
  });
}


export function useVendorCredits(vendorId: string | null) {
  const { key, enabled, ws } = useWorkspaceKey("vendor-credits", vendorId ?? undefined);
  return useQuery({ queryKey: key, queryFn: () => apDashboardApi.listVendorCredits(vendorId!), enabled: enabled && !!vendorId, staleTime: 20_000 });
}
export function useCreateVendorCredit(vendorId: string) {
  const qc = useQueryClient(); const { ws } = useWorkspaceKey();
  return useMutation({ mutationFn: (body: import("@/api/ap").VendorCreditCreate) => apDashboardApi.createVendorCredit(vendorId, body), onSuccess: () => { qc.invalidateQueries({ queryKey: ["vendor-credits", vendorId, ws] }); toast.success("Vendor credit created."); }, onError: (e) => toast.error(getErrorMessage(e, "Could not create vendor credit.")) });
}
export function useApplyVendorCredit(vendorId: string) {
  const qc = useQueryClient(); const { ws } = useWorkspaceKey();
  return useMutation({ mutationFn: (v: { creditId: string; document_id: string; amount: number }) => apDashboardApi.applyVendorCredit(v.creditId, { document_id: v.document_id, amount: v.amount }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["vendor-credits", vendorId, ws] }); qc.invalidateQueries({ queryKey: ["vendor-statement", vendorId, ws] }); toast.success("Credit applied to bill."); }, onError: (e) => toast.error(getErrorMessage(e, "Could not apply vendor credit.")) });
}
export function useCancelVendorCredit(vendorId: string) {
  const qc = useQueryClient(); const { ws } = useWorkspaceKey();
  return useMutation({ mutationFn: (v: { creditId: string; reason: string }) => apDashboardApi.cancelVendorCredit(v.creditId, v.reason), onSuccess: () => { qc.invalidateQueries({ queryKey: ["vendor-credits", vendorId, ws] }); toast.success("Vendor credit cancelled."); }, onError: (e) => toast.error(getErrorMessage(e, "Could not cancel vendor credit.")) });
}
