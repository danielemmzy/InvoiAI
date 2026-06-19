// ─────────────────────────────────────────────
// InvoiAI — Global TypeScript Types
// Mirror of backend Pydantic models
// ─────────────────────────────────────────────

export interface User {
  user_id: string;
  email: string;
  plan: "free" | "starter" | "pro";
  usage: UsageSummary;
}

export interface UsageSummary {
  used: number;
  limit: number;
  remaining: number;
  plan: string;
  month: string;
  limit_reached: boolean;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user_id: string;
  email: string;
  plan: string;
}

export interface StructuredDocument {
  industry: string;
  document_type: string;
  sections: Record<string, unknown>;
  raw_totals: Record<string, number>;
  extraction_confidence: "high" | "medium" | "low";
}

export interface UploadResponse {
  invoice_id: string;
  status: string;
  document_type?: string;
  structured_data?: StructuredDocument;
  validation_warnings: string[];
}

export interface HistoryItem {
  id: string;
  file_name: string;
  file_type: "pdf" | "image";
  industry: string;
  document_type?: string;
  status: "processing" | "done" | "failed";
  validation_warnings: string[];
  created_at?: string;
  sheets_url?: string;
}

export interface HistoryResponse {
  documents: HistoryItem[];
  count: number;
  offset: number;
  limit: number;
}

export interface Industry {
  value: string;
  label: string;
}

export interface Subscription {
  plan: string;
  status: string;
  current_period_end?: string;
  cancel_at_period_end?: boolean;
}

export interface BillingInfo {
  plan: string;
  usage: UsageSummary;
  subscription?: Subscription;
}

export interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

export interface SheetsExportResponse {
  sheets_url: string;
  message: string;
}