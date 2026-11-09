import { client } from "@/api/client";

export type OrganizationProfile = {
  id: string;
  name: string;
  slug: string;
  plan: string;
  industry?: string | null;
  company_size?: string | null;
  country?: string | null;
  currency: string;
  tax_id?: string | null;
  logo_url?: string | null;
  website?: string | null;
};

export type OrganizationSettings = {
  default_currency: string;
  supported_currencies: string[];
  timezone: string;
  fiscal_year_start_month: number;
  date_format: string;
  number_format: string;
  default_language: string;
  auto_analyze: boolean;
  ocr_language: string;
  default_industry: string;
  supported_document_types: string[];
  duplicate_threshold: number;
  duplicate_window_days: number;
  duplicate_amount_tolerance: number;
  fraud_sensitivity: string;
  auto_reject_fraud_score: number;
  fraud_alert_email?: string | null;
  auto_create_vendors: boolean;
  vendor_match_threshold: number;
  require_vendor_verification: boolean;
  ai_enabled: boolean;
  ai_model_preference: string;
  ai_temperature: number;
  enable_embeddings: boolean;
  copilot_enabled: boolean;
  copilot_memory_days: number;
  copilot_max_context_docs: number;
  analytics_enabled: boolean;
  analytics_retention_months: number;
  email_notifications: boolean;
  notification_email?: string | null;
  slack_webhook_url?: string | null;
  outbound_webhook_url?: string | null;
  brand_color?: string | null;
  custom_domain?: string | null;
  sso_provider?: string | null;
  sso_config: Record<string, unknown>;
  policy_settings: Record<string, unknown>;
};

export type OrganizationSettingsResponse = {
  organization: OrganizationProfile;
  settings: OrganizationSettings;
  permissions: string[];
};

export type OrganizationSettingsUpdate = {
  organization?: Partial<OrganizationProfile>;
  settings?: Partial<OrganizationSettings>;
  policy_settings?: Record<string, unknown>;
};

export const settingsApi = {
  get: async () =>
    (await client.get<OrganizationSettingsResponse>("/organization-settings")).data,
  update: async (payload: OrganizationSettingsUpdate) =>
    (await client.patch<OrganizationSettingsResponse>("/organization-settings", payload)).data,
};
