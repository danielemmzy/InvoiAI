import { client } from "./client";

export type ApprovalRecommendation = "auto_approve" | "review" | "reject";
export type RiskLevel = "low" | "medium" | "high";

export interface ApprovalQueueItem {
  approver_id: string;
  org_id: string;
  workflow_id: string;
  step_id: string;
  step_name: string;
  step_number: number;
  due_date: string | null;
  document_id: string;
  document_number: string | null;
  vendor_name: string | null;
  total_amount: number;
  currency: string;
  document_type: string;
  // Nullable: the approval_queue view LEFT JOINs document_analyses, so a
  // step that reaches approval before its analysis row exists comes back
  // with these as null rather than absent.
  health_score: number | null;
  risk_level: RiskLevel | null;
  recommendation: ApprovalRecommendation | null;
  is_urgent: boolean;
  initiated_at: string;
}

export const approvalsApi = {
  listPending: async () => (await client.get<ApprovalQueueItem[]>("/approvals")).data,
  listOverdue: async () => (await client.get<ApprovalQueueItem[]>("/approvals/overdue")).data,
  decide: async (stepId: string, decision: "approved" | "rejected", comment?: string) =>
    (await client.post(`/approvals/${stepId}/decide`, { decision, comment })).data,
};
