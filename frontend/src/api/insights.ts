import { client } from "./client";

export type InsightType = "overdue" | "price_increase" | "anomaly" | "cashflow" | "duplicate";
export type InsightSeverity = "info" | "warning" | "critical";

export interface InsightRow {
  id: string;
  insight_type: InsightType;
  severity: InsightSeverity;
  title: string;
  description: string;
  data: Record<string, unknown>;
  affected_resource_type: string | null;
  affected_resource_id: string | null;
  recommended_action: string | null;
  is_read: boolean;
  is_dismissed: boolean;
  expires_at: string | null;
  created_at: string;
}

export const insightsApi = {
  list: async () => (await client.get<InsightRow[]>("/insights")).data,
  generate: async () => (await client.post<InsightRow[]>("/insights/generate")).data,
  dismiss: async (id: string) => (await client.patch(`/insights/${id}`, { is_dismissed: true })).data,
};
