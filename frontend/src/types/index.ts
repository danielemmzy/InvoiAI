// ─────────────────────────────────────────────
// InvoiAI — Global TypeScript Types
// Mirror of backend Pydantic models
// ─────────────────────────────────────────────

export interface User {
  user_id: string;
  email: string;
  plan: "free" | "starter" | "pro" | "business" | "enterprise";
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



export interface StructuredDocument {
  industry: string;
  document_type: string;
  sections: Record<string, unknown>;
  raw_totals: Record<string, number | string | null>;
  extraction_confidence: "high" | "medium" | "low";
}

export interface UploadResponse {
  invoice_id: string;
  status: string;
  document_type?: string;
  structured_data?: StructuredDocument;
  validation_warnings: string[];
  file_name?: string;
  industry?: string;
  pipeline_stage?: string;
  processing_step?: string | null;
  processing_message?: string | null;
  processing_progress?: number | null;
  error_message?: string | null;
  created_at?: string;
}

export interface HistoryItem {
  id: string;
  file_name: string;
  file_type: "pdf" | "image";
  industry: string;
  document_type?: string;
  status: string;
  pipeline_stage?: string | null;
  processing_step?: string | null;
  processing_message?: string | null;
  processing_progress?: number | null;
  error_message?: string | null;
  validation_warnings: string[];
  created_at?: string;
  sheets_url?: string;
  vendor_name?: string | null;
  document_number?: string | null;
  document_date?: string | null;
  due_date?: string | null;
  currency?: string | null;
  subtotal?: number | string | null;
  total_amount?: number | string | null;
  amount_due?: number | string | null;
  total_quantity?: number | string | null;
  line_item_count?: number;
  account_id?: string | null;
  account_code?: string | null;
  account_name?: string | null;
  classification_confidence?: number | string | null;
  human_review_status?: string | null;
  intelligence_status?: string | null;
  capture_status?: string | null;
  capture_progress?: number | null;
  capture_error?: string | null;
}

export interface HistoryResponse {
  documents: HistoryItem[];
  count: number;
  offset: number;
  limit: number;
}

export interface DocumentIntelligence {
  document: {
    id: string; file_name?: string; document_type?: string; status?: string; pipeline_stage?: string; workflow_route?: string | null;
    processing_step?: string | null; processing_message?: string | null; processing_progress?: number | null; error_message?: string | null;
    validation_warnings?: string[]; vendor_id?: string | null; vendor_name?: string | null; document_number?: string | null; document_date?: string | null; due_date?: string | null;
    subtotal?: number | string | null; tax_rate?: number | string | null; tax_amount?: number | string | null; discount_amount?: number | string | null; total_amount?: number | string | null; amount_paid?: number | string | null; amount_due?: number | string | null;
    currency?: string | null; payment_terms?: string | null; payment_method?: string | null; ap_enabled?: boolean;
  };
  ocr: { raw_text?: string; pages?: Array<{ page_number?: number; text?: string }>; tables_detected?: Array<Record<string, unknown>>; key_value_pairs?: Record<string, unknown>; page_count?: number; confidence_score?: number | string; engine?: string; engine_version?: string; processing_ms?: number; } | null;
  line_items: Array<Record<string, unknown>>;
  structured_data?: Record<string, unknown> | null;
  analysis: any | null;
  embedding: { model_used?: string; created_at?: string } | null;
  vendor: any | null;
  vendor_embedding_ready: boolean;
  ready: boolean;
  actions: string[];
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

export interface AuthResponse {
  user_id: string;
  email: string;
  org_id?: string | null;
  plan?: string | null;
  is_verified?: boolean;
  mfa_enrollment_required?: boolean;
  mfa_challenge_required?: boolean;
}

export interface SignupResponse {
  user_id?: string;
  email?: string;
  plan?: string;
  requires_email_verification?: boolean;
  verification_email_sent?: boolean;
  otp_expires_in_seconds?: number | null;
  resend_cooldown_seconds?: number | null;
}

export interface VerifyOtpResponse {
  verified: boolean;
  message: string;
}

export interface ResendOtpResponse {
  message: string;
  code_sent: boolean;
  retry_after_seconds: number | null;
}

export interface SheetsExportResponse {
  sheets_url: string;
  message: string;
}
export * from "./workspace";
