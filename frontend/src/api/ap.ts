import client from "./client";

export interface ChartOfAccount {
  id: string;
  account_code: string;
  account_name: string;
  account_type?: string;
  account_subtype?: string | null;
  external_id?: string | null;
  is_active: boolean;
  is_postable: boolean;
  source?: string;
  parent_id?: string | null;
}

export interface APException {
  id: string;
  document_id: string;
  exception_type: string;
  severity?: string;
  status: string;
  message?: string;
  title?: string;
  description?: string | null;
  resolution_note?: string | null;
  created_at?: string;
  expected_value?: string | null;
  actual_value?: string | null;
  variance?: string | null;
  details?: Record<string, unknown>;
  document?: { id: string; document_number?: string | null; vendor_name?: string | null; file_name?: string | null; total_amount?: number | string | null; currency?: string | null; ap_status?: string | null } | null;
}

export interface APStatus {
  id: string;
  ap_enabled?: boolean;
  ap_status?: string | null;
  ap_match_mode?: "auto" | "non_po" | "two_way" | "three_way" | null;
  match_status?: string | null;
  two_way_match_passed?: boolean | null;
  three_way_match_passed?: boolean | null;
  purchase_order_id?: string | null;
  goods_receipt_id?: string | null;
  gl_coding_status?: string | null;
  erp_bill_id?: string | null;
  payment_ready_at?: string | null;
  processing_step?: string | null;
  processing_message?: string | null;
  processing_progress?: number | null;
  error_message?: string | null;
  updated_at?: string | null;
}

export type APMatchMode = "auto" | "non_po" | "two_way" | "three_way";
export interface APRunRequest {
  match_mode: APMatchMode;
  purchase_order_id?: string | null;
  goods_receipt_id?: string | null;
}

export interface APReferenceUploadResponse {
  document_id: string;
  reference_type: "purchase_order" | "goods_receipt";
  status: string;
}

export interface APEmailAddress {
  id?: string;
  email_address?: string;
  is_active?: boolean;
  configured?: boolean;
}

export interface InvoiceCoding {
  id: string;
  document_id: string;
  line_item_id?: string | null;
  gl_account_id?: string | null;
  account_code?: string | null;
  account_name?: string | null;
  confidence?: number | null;
  status?: string;
  source?: string;
  reasoning?: string | null;
}

export const apApi = {
  listChartOfAccounts: async (includeInactive = false) =>
    (await client.get<ChartOfAccount[]>("/ap/chart-of-accounts", { params: includeInactive ? { include_inactive: true } : undefined })).data,
  syncChartOfAccounts: async () => (await client.post("/ap/chart-of-accounts/sync")).data,
  seedChartOfAccounts: async () => (await client.post<{ created: number; skipped: number }>("/ap/chart-of-accounts/seed")).data,
  createChartOfAccount: async (body: Partial<ChartOfAccount> & { account_code: string; account_name: string }) =>
    (await client.post<ChartOfAccount>("/ap/chart-of-accounts", body)).data,
  updateChartOfAccount: async (id: string, body: Partial<ChartOfAccount>) =>
    (await client.patch<ChartOfAccount>(`/ap/chart-of-accounts/${id}`, body)).data,
  deactivateChartOfAccount: async (id: string) => (await client.delete<{ id: string; is_active: boolean }>(`/ap/chart-of-accounts/${id}`)).data,
  listExceptions: async () => (await client.get<APException[]>("/ap/exceptions")).data,
  getExceptions: async (documentId: string) => (await client.get<APException[]>(`/ap/exceptions/${documentId}`)).data,
  resolveException: async (id: string, note = "") => (await client.post(`/ap/exceptions/${id}/resolve`, { note })).data,
  waiveException: async (id: string, note = "") => (await client.post(`/ap/exceptions/${id}/waive`, { note })).data,
  getCodings: async (documentId: string) => (await client.get<InvoiceCoding[]>(`/ap/codings/${documentId}`)).data,
  approveCodings: async (documentId: string) => (await client.post(`/ap/codings/${documentId}/approve`)).data,
  saveLineCoding: async (documentId: string, lineItemId: string, body: { gl_account_id: string; amount?: number }) =>
    (await client.put<{ saved: boolean; gl_account: any }>(`/ap/codings/${documentId}/line/${lineItemId}`, body)).data,
  createCodingRule: async (body: {
    name: string;
    description?: string;
    vendor_id?: string;
    description_pattern?: string;
    sku_pattern?: string;
    gl_account_id: string;
    department_id?: string;
    cost_center_id?: string;
    project_id?: string;
    tax_code_id?: string;
    priority?: number;
  }) => (await client.post("/ap/coding-rules", body)).data,
  getStatus: async (documentId: string) => (await client.get<APStatus>(`/ap/documents/${documentId}/status`)).data,
  selectInvoice: async (documentId: string) => (await client.post(`/ap/documents/${documentId}/select`)).data,
  run: async (documentId: string, body: APRunRequest) => (await client.post(`/ap/documents/${documentId}/run`, body)).data,
  submitForApproval: async (documentId: string) => (await client.post(`/ap/documents/${documentId}/submit-for-approval`)).data,
  listMatchingPurchaseOrders: async (vendorId?: string) => (await client.get(`/ap/matching/purchase-orders${vendorId ? `?vendor_id=${encodeURIComponent(vendorId)}` : ""}`)).data,
  listMatchingReceipts: async (purchaseOrderId: string) => (await client.get(`/ap/matching/receipts/${purchaseOrderId}`)).data,
  uploadReferenceDocument: async (file: File, referenceType: "purchase_order" | "goods_receipt") => {
    const form = new FormData();
    form.append("file", file);
    form.append("reference_type", referenceType);
    return (await client.post<APReferenceUploadResponse>("/ap/reference-documents/upload", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
  },
  convertReferenceDocument: async (sourceDocumentId: string, purchaseOrderId?: string) => (await client.post(`/ap/reference-documents/${sourceDocumentId}/convert`, purchaseOrderId ? { purchase_order_id: purchaseOrderId } : {})).data,
  getEmailAddress: async () => (await client.get<APEmailAddress>("/ap/email-address")).data,
  createEmailAddress: async () => (await client.post<APEmailAddress>("/ap/email-address")).data,
  rotateEmailAddress: async () => (await client.post<APEmailAddress>("/ap/email-address/rotate")).data,
};

/**
 * Compatibility facade for older AP automation hooks.
 * The canonical AP API remains `apApi`; this facade prevents duplicate
 * API implementations while keeping legacy automation screens working.
 */
export type APAutomationRunRequest = APRunRequest;

export const apAutomationApi = {
  prepare: async (documentId: string) =>
    (await client.post(`/ap/documents/${documentId}/prepare`)).data,

  run: async (documentId: string, payload: APAutomationRunRequest) =>
    apApi.run(documentId, payload),

  listGoodsReceipts: async (purchaseOrderId: string) =>
    apApi.listMatchingReceipts(purchaseOrderId),
};

export const integrationsApi = {
  list: async () => (await client.get<IntegrationConnection[]>("/integrations")).data,
  syncSuppliers: async (provider: IntegrationProvider) =>
    (await client.post<SupplierImportResult>(`/integrations/${provider}/sync/vendors`)).data,
  connectQuickBooks: () => "/api/bff/integrations/quickbooks/connect",
  disconnect: async (id: string) => { await client.delete(`/integrations/${id}`); },
};

export type IntegrationProvider = "quickbooks" | "xero" | "sage";
export interface SupplierImportResult {
  total: number;
  imported: number;
  updated: number;
  skipped: number;
  failed: number;
  errors?: { resource: string; external_id: string | null; error: string }[];
  completed_at?: string;
}
export interface IntegrationConnection {
  id: string;
  provider: IntegrationProvider;
  is_active: boolean;
  account_name?: string | null;
  metadata?: Record<string, unknown>;
}

/* ════════════════════════════════════════════════════════════
   AP Dashboard — backed by app/routers/ap.py and the
   APDashboardService read model.
   ════════════════════════════════════════════════════════════ */

export type InvoiceStatusFilter =
  | "awaiting_approval" | "approved" | "match_exception" | "coding_exception"
  | "payment_ready" | "paid" | "overdue" | "rejected";

export interface APDashboardFilters {
  date_from?: string;
  date_to?: string;
  vendor_id?: string;
  status?: InvoiceStatusFilter;
  priority?: "low" | "medium" | "high" | "urgent";
  // Filters invoices by their original transaction currency.
  currency?: string;
  // Converts dashboard aggregates into this reporting currency without changing invoice currency.
  reporting_currency?: string;
  search?: string;
}

export interface APSummary {
  total_vendors: number;
  open_vendors: number;
  total_invoices: number;
  open_invoices: number;
  total_amount: number;
  total_paid: number;
  open_amount: number;
  overdue_amount: number;
  currency: string;
  payables_by_month: { month: string; billed: number; paid: number }[];
  payable_turnover_days: number;
  payable_turnover_trend: { month: string; days: number }[];
  by_currency: { currency: string; amount: number }[];
}

export interface APInvoiceRow {
  id: string;
  vendor_id: string;
  vendor_name: string;
  invoice_number: string | null;
  amount: number;
  currency: string;
  status: InvoiceStatusFilter | string;
  priority: "low" | "medium" | "high" | "urgent";
  tags: string[];
  issue_date: string | null;
  due_date: string | null;
  health_score?: number | null;
  risk_level?: "low" | "medium" | "high" | null;
  document_id: string;
  reporting_amount?: number | null;
  reporting_currency?: string | null;
  fx_rate?: number | null;
  fx_rate_date?: string | null;
}

export interface APInvoiceList {
  items: APInvoiceRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface TopVendor {
  vendor_id: string;
  vendor_name: string;
  current_balance: number;
  overdue_balance: number;
  currency: string;
  risk_score: number;
  risk_level: "low" | "medium" | "high";
}

export interface AgingBucket {
  bucket: "current" | "1_30" | "31_60" | "61_90" | "90_plus";
  label: string;
  amount: number;
  invoice_count: number;
}

export interface AgingRow {
  vendor_id: string;
  vendor_name: string;
  current: number;
  d1_30: number;
  d31_60: number;
  d61_90: number;
  d90_plus: number;
  total: number;
}

export interface AgingResponse {
  buckets: AgingBucket[];
  rows: AgingRow[];
  currency: string;
}

export interface VendorStatement {
  vendor_id: string;
  vendor_name: string;
  currency: string;
  credit_limit: number | null;
  total_purchases: number;
  total_payments: number;
  total_balance: number;
  open_invoices: number;
  avg_overdue_days: number;
  risk_score: number;
  risk_level: "low" | "medium" | "high";
  fraud_flags: number;
  trend: { month: string; billed: number; paid: number }[];
  balance_by_status: { status: string; amount: number }[];
  recent_invoices: APInvoiceRow[];
}

export interface VendorListRow {
  id: string;
  name: string;
  total_spend: number;
  open_balance: number;
  currency: string;
  risk_score: number;
  risk_level: "low" | "medium" | "high";
  fraud_flags: number;
  is_preferred: boolean;
  is_blocked: boolean;
}

function toQuery<T extends object>(filters?: T) {
  if (!filters) return "";

  const params = new URLSearchParams();

  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") {
      params.set(k, String(v));
    }
  });

  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export interface VendorCreditApplication { id: string; document_id: string; amount: string | number; currency: string; created_at: string; }
export interface VendorCredit { id: string; vendor_id: string; credit_number?: string | null; reason?: string | null; amount: string | number; remaining_amount: string | number; currency: string; issued_at: string; expires_at?: string | null; status: "open" | "partially_applied" | "applied" | "expired" | "cancelled"; notes?: string | null; created_at: string; applications?: VendorCreditApplication[]; events?: { id: string; actor_id?: string | null; event_type: string; details?: Record<string, unknown>; created_at: string }[]; }
export interface VendorCreditCreate { amount: number; currency: string; credit_number?: string; reason?: string; issued_at?: string; expires_at?: string; notes?: string; }

export const apDashboardApi = {
  getSummary: async (filters?: APDashboardFilters) =>
    (await client.get<APSummary>(`/ap/dashboard/summary${toQuery(filters)}`)).data,

  listInvoices: async (filters?: APDashboardFilters & { limit?: number; offset?: number }) =>
    (await client.get<APInvoiceList>(`/ap/dashboard/invoices${toQuery(filters)}`)).data,

  getTopVendors: async (filters?: APDashboardFilters) =>
    (await client.get<TopVendor[]>(`/ap/dashboard/top-vendors${toQuery(filters)}`)).data,

  getAging: async (filters?: APDashboardFilters) =>
    (await client.get<AgingResponse>(`/ap/dashboard/aging${toQuery(filters)}`)).data,

  getVendorStatement: async (vendorId: string) =>
    (await client.get<VendorStatement>(`/vendors/${vendorId}/statement`)).data,
  listVendorCredits: async (vendorId: string) => (await client.get<VendorCredit[]>(`/vendors/${vendorId}/credits`)).data,
  createVendorCredit: async (vendorId: string, body: VendorCreditCreate) => (await client.post<VendorCredit>(`/vendors/${vendorId}/credits`, body)).data,
  applyVendorCredit: async (creditId: string, body: { document_id: string; amount: number }) => (await client.post(`/vendors/credits/${creditId}/apply`, body)).data,
  cancelVendorCredit: async (creditId: string, reason: string) => (await client.post(`/vendors/credits/${creditId}/cancel`, { reason })).data,
  getVendorCreditEvents: async (creditId: string) => (await client.get(`/vendors/credits/${creditId}/events`)).data,

  listVendors: async (filters?: { search?: string; risk_level?: string }) => {
    const params = new URLSearchParams();
    if (filters?.search) params.set("query", filters.search);
    if (filters?.risk_level) params.set("risk_level", filters.risk_level);
    const query = params.toString();
    return (await client.get<VendorListRow[]>(`/vendors${query ? `?${query}` : ""}`)).data;
  },
};

export namespace apDashboardApi {
  export type SummaryFilters = APDashboardFilters;
  export type InvoiceFilters = APDashboardFilters & { limit?: number; offset?: number };
}

/* ════════════════════════════════════════════════════════════
   AP Workflow Engine — routing rules, approval groups (pooled
   approvers), payment authorization queue, and invoice tagging.
   Backed by app/routers/ap_workflow.py.
   ════════════════════════════════════════════════════════════ */

export type ApprovalRuleScope = "bill" | "payment";
export type ApproverType = "user" | "role" | "group";
export type ApprovalExecutionMode = "sequential" | "parallel" | "any_one" | "group";
export type PaymentAuthorizationStatus =
  | "authorized" | "blocked" | "needs_review" | "override_required";
export type PaymentInstructionStatus =
  | "requested" | "scheduled" | "pending_approval" | "approved_for_payment"
  | "pending_authorization" | "authorized" | "blocked" | "processing"
  | "paid" | "returned" | "failed" | "cancelled" | "reconciled";
export type VendorDocumentRequestType = "w9" | "bank_verification";
export type VendorDocumentRequestStatus = "pending" | "submitted" | "verified" | "rejected" | "expired";

export interface ApprovalRule {
  id: string;
  org_id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  priority: number;
  scope: ApprovalRuleScope;
  min_amount?: number | null;
  max_amount?: number | null;
  vendor_id?: string | null;
  department?: string | null;
  cost_center?: string | null;
  location?: string | null;
  document_type?: string | null;
  risk_level?: string | null;
  requires_po?: boolean | null;
  step_number: number;
  step_name: string;
  execution_mode: ApprovalExecutionMode;
  approver_type: ApproverType;
  approver_id?: string | null;
  approver_role?: string | null;
  approver_group_id?: string | null;
  conditions?: Record<string, unknown> | null;
  actions?: Record<string, unknown>[] | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
}

export type ApprovalRuleCreate = Omit<
  ApprovalRule,
  "id" | "org_id" | "created_by" | "created_at" | "updated_at"
>;

export type ApprovalRuleUpdate = Partial<
  Omit<ApprovalRuleCreate, "scope">
>;

export interface ApprovalGroup {
  id: string;
  org_id: string;
  name: string;
  description?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApprovalGroupMember {
  id: string;
  group_id: string;
  user_id: string;
  added_at: string;
}

export interface ApprovalStep {
  id: string;
  workflow_id: string;
  org_id: string;
  step_number: number;
  step_name: string;
  approver_id?: string | null;
  approver_role: string;
  approver_group_id?: string | null;
  claimed_by?: string | null;
  claimed_at?: string | null;
  auto_escalated: boolean;
  spending_limit?: number | null;
  decision?: string | null;
  decided_at?: string | null;
  comment?: string | null;
}

export interface PaymentQueueRow {
  document_id: string;
  vendor_name: string | null;
  amount: number | null;
  currency: string | null;
  document_number: string | null;
  due_date: string | null;
  erp_bill_id: string | null;
  authorization_status: PaymentAuthorizationStatus;
  blocked_reasons: string[];
}

export interface PaymentAuthorization {
  id: string;
  org_id: string;
  document_id: string;
  status: PaymentAuthorizationStatus;
  blocked_reasons: string[];
  checks: Record<string, boolean>;
  authorized_by?: string | null;
  authorized_at?: string | null;
  override_by?: string | null;
  override_at?: string | null;
  override_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface InvoiceComment {
  id: string;
  org_id: string;
  document_id: string;
  author_id: string;
  body: string;
  mentioned_user_ids: string[];
  created_at: string;
}

export const apRulesApi = {
  list: async (scope?: ApprovalRuleScope) =>
    (await client.get<ApprovalRule[]>(`/ap/rules${toQuery(scope ? { scope } : undefined)}`)).data,
  create: async (payload: ApprovalRuleCreate) =>
    (await client.post<ApprovalRule>("/ap/rules", payload)).data,
  update: async (ruleId: string, payload: ApprovalRuleUpdate) =>
    (await client.patch<ApprovalRule>(`/ap/rules/${ruleId}`, payload)).data,
  remove: async (ruleId: string) => { await client.delete(`/ap/rules/${ruleId}`); },
};

export const apGroupsApi = {
  list: async () => (await client.get<ApprovalGroup[]>("/ap/groups")).data,
  create: async (name: string, description?: string) =>
    (await client.post<ApprovalGroup>("/ap/groups", { name, description })).data,
  remove: async (groupId: string) => { await client.delete(`/ap/groups/${groupId}`); },
  listMembers: async (groupId: string) =>
    (await client.get<ApprovalGroupMember[]>(`/ap/groups/${groupId}/members`)).data,
  addMember: async (groupId: string, userId: string) =>
    (await client.post(`/ap/groups/${groupId}/members`, { user_id: userId })).data,
  removeMember: async (groupId: string, userId: string) => {
    await client.delete(`/ap/groups/${groupId}/members/${userId}`);
  },
  claimStep: async (stepId: string) =>
    (await client.post<ApprovalStep>(`/ap/steps/${stepId}/claim`)).data,
};

export const paymentAuthorizationApi = {
  getQueue: async () => (await client.get<PaymentQueueRow[]>("/ap/payments/queue")).data,
  evaluate: async (documentId: string) =>
    (await client.post<PaymentAuthorization>(`/ap/payments/${documentId}/evaluate`)).data,
  override: async (documentId: string, reason: string) =>
    (await client.post<PaymentAuthorization>(`/ap/payments/${documentId}/override`, { reason })).data,
};

export const invoiceCommentsApi = {
  list: async (documentId: string) =>
    (await client.get<InvoiceComment[]>(`/ap/documents/${documentId}/comments`)).data,
  add: async (documentId: string, body: string, mentionedUserIds: string[] = []) =>
    (await client.post<InvoiceComment>(`/ap/documents/${documentId}/comments`, {
      body,
      mentioned_user_ids: mentionedUserIds,
    })).data,
};

export interface MemberApprovalLimits {
  spending_limit?: number | null;
  payment_approval_limit?: number | null;
  supervisor_id?: string | null;
}

export const memberApprovalLimitsApi = {
  set: async (membershipId: string, payload: MemberApprovalLimits) =>
    (await client.patch(`/members/${membershipId}/approval-limits`, payload)).data,
};

/* ════════════════════════════════════════════════════════════
   Payment instructions — the actual payment record (separate
   from the payment_authorizations compliance gate above), and
   vendor W-9 / bank-change control workflows.
   ════════════════════════════════════════════════════════════ */

export interface PaymentInstruction {
  id: string;
  org_id: string;
  document_id: string;
  vendor_id?: string | null;
  amount: number;
  currency: string;
  payment_method?: string | null;
  scheduled_date?: string | null;
  requested_by?: string | null;
  approved_by?: string | null;
  authorized_by?: string | null;
  approval_workflow_id?: string | null;
  provider?: string | null;
  provider_payment_id?: string | null;
  idempotency_key: string;
  status: PaymentInstructionStatus;
  failure_reason?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface VendorDocumentRequest {
  id: string;
  org_id: string;
  vendor_id: string;
  request_type: VendorDocumentRequestType;
  status: VendorDocumentRequestStatus;
  token: string;
  requested_by?: string | null;
  requested_at: string;
  submitted_at?: string | null;
  document_url?: string | null;
  submitted_data: Record<string, unknown>;
  verified_by?: string | null;
  verified_at?: string | null;
  rejection_reason?: string | null;
  expires_at: string;
  updated_at: string;
}

export interface PaymentInstructionEvent {
  id: string;
  org_id: string;
  payment_instruction_id: string;
  from_status?: PaymentInstructionStatus | null;
  to_status: PaymentInstructionStatus;
  reason?: string | null;
  actor_id?: string | null;
  created_at: string;
}

export interface PaymentInstructionCreateInput {
  payment_method?: string | null;
  scheduled_date?: string | null;
  idempotency_key?: string | null;
}

export const paymentInstructionsApi = {
  listForDocument: async (documentId: string) =>
    (await client.get<PaymentInstruction[]>(`/ap/payments/${documentId}/instructions`)).data,
  create: async (documentId: string, input: PaymentInstructionCreateInput = {}) =>
    (await client.post<PaymentInstruction>(`/ap/payments/${documentId}/instructions`, input)).data,
  listEvents: async (instructionId: string) =>
    (await client.get<PaymentInstructionEvent[]>(`/ap/payments/instructions/${instructionId}/events`)).data,
  cancel: async (instructionId: string, reason: string) =>
    (await client.post<PaymentInstruction>(`/ap/payments/instructions/${instructionId}/cancel`, { reason })).data,
  reconcile: async (instructionId: string) =>
    (await client.post<PaymentInstruction>(`/ap/payments/instructions/${instructionId}/reconcile`)).data,
};

export const vendorControlsApi = {
  listRequests: async (vendorId: string) =>
    (await client.get<VendorDocumentRequest[]>(`/ap/vendors/${vendorId}/document-requests`)).data,
  requestDocument: async (vendorId: string, requestType: VendorDocumentRequestType) =>
    (await client.post<VendorDocumentRequest>(`/ap/vendors/${vendorId}/document-requests`, { request_type: requestType })).data,
  verifyBankChange: async (requestId: string, approve: boolean, reason?: string) =>
    (await client.post<VendorDocumentRequest>(`/ap/vendors/document-requests/${requestId}/verify-bank-change`, { approve, reason })).data,
};

/* Public, token-gated vendor portal — no BFF/session auth applies.
   These use the Next.js same-origin public proxy, which forwards to
   FastAPI /api/public/vendor-portal/* without requiring a session. */

const VENDOR_PORTAL_BASE = "/api/public/vendor-portal";

export const vendorPortalApi = {
  get: async (token: string) => {
    const res = await fetch(`${VENDOR_PORTAL_BASE}/${token}`);
    if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "This link is invalid.");
    return res.json() as Promise<{ request_type: VendorDocumentRequestType; vendor_name: string | null }>;
  },
  submitW9: async (token: string, documentUrl: string) => {
    const res = await fetch(`${VENDOR_PORTAL_BASE}/${token}/submit-w9`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_url: documentUrl }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "Submission failed.");
    return res.json() as Promise<{ status: VendorDocumentRequestStatus }>;
  },
  submitBankVerification: async (
    token: string,
    payload: { account_holder_name: string; bank_name: string; account_number_last4: string; routing_number: string },
  ) => {
    const res = await fetch(`${VENDOR_PORTAL_BASE}/${token}/submit-bank-verification`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "Submission failed.");
    return res.json() as Promise<{ status: VendorDocumentRequestStatus }>;
  },
};

export interface AccountingTaxMapping {
  id: string;
  provider: "quickbooks" | "xero";
  source_tax_rate: number | string;
  source_tax_code?: string | null;
  external_tax_code_id: string;
  external_tax_code_name?: string | null;
  is_active: boolean;
}
export const accountingTaxMappingsApi = {
  list: async (provider?: "quickbooks" | "xero") => (await client.get<AccountingTaxMapping[]>(`/ap/accounting-tax-mappings${provider ? `?provider=${provider}` : ""}`)).data,
  save: async (mapping: Omit<AccountingTaxMapping, "id" | "is_active">) => (await client.post<AccountingTaxMapping>("/ap/accounting-tax-mappings", mapping)).data,
  deactivate: async (id: string) => (await client.delete(`/ap/accounting-tax-mappings/${id}`)).data,
};
