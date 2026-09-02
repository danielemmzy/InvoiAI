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
  resolution_note?: string | null;
  created_at?: string;
}

export interface APStatus {
  id: string;
  ap_status?: string | null;
  match_status?: string | null;
  gl_coding_status?: string | null;
  erp_bill_id?: string | null;
  payment_ready_at?: string | null;
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
  listChartOfAccounts: async () => (await client.get<ChartOfAccount[]>("/ap/chart-of-accounts")).data,
  syncChartOfAccounts: async () => (await client.post("/ap/chart-of-accounts/sync")).data,
  listExceptions: async () => (await client.get<APException[]>("/ap/exceptions")).data,
  getExceptions: async (documentId: string) => (await client.get<APException[]>(`/ap/exceptions/${documentId}`)).data,
  resolveException: async (id: string, note = "") => (await client.post(`/ap/exceptions/${id}/resolve`, { note })).data,
  waiveException: async (id: string, note = "") => (await client.post(`/ap/exceptions/${id}/waive`, { note })).data,
  getCodings: async (documentId: string) => (await client.get<InvoiceCoding[]>(`/ap/codings/${documentId}`)).data,
  approveCodings: async (documentId: string) => (await client.post(`/ap/codings/${documentId}/approve`)).data,
  getStatus: async (documentId: string) => (await client.get<APStatus>(`/ap/documents/${documentId}/status`)).data,
  getEmailAddress: async () => (await client.get("/ap/email-address")).data,
  createEmailAddress: async () => (await client.post("/ap/email-address")).data,
};

export const integrationsApi = {
  list: async () => (await client.get("/integrations")).data,
  connectQuickBooks: () => "/api/bff/integrations/quickbooks/connect",
  disconnect: async (id: string) => { await client.delete(`/integrations/${id}`); },
};

/* ════════════════════════════════════════════════════════════
   AP Dashboard — see BACKEND_INTEGRATION_AP_DASHBOARD.md for
   the endpoint contracts this module assumes. None of these
   routes exist on the backend yet; the doc specifies exactly
   what each one needs to return.
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
  currency?: string;
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

  listVendors: async (filters?: { search?: string; risk_level?: string }) =>
    (await client.get<VendorListRow[]>(`/vendors${toQuery(filters)}`)).data,
};

export namespace apDashboardApi {
  export type SummaryFilters = APDashboardFilters;
  export type InvoiceFilters = APDashboardFilters & { limit?: number; offset?: number };
}
