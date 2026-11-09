import client from "./client";
import type { CompanySize, WorkspaceSummary, WorkspaceType } from "@/types/workspace";

export const workspacesApi = {
  list: async (): Promise<WorkspaceSummary[]> => {
    const { data } = await client.get<WorkspaceSummary[]>("/workspaces");
    return data;
  },
  create: async (input: {
    type: WorkspaceType;
    name?: string;
    currency?: string;
    country?: string;
    company_size?: CompanySize;
  }): Promise<WorkspaceSummary> => {
    const { data } = await client.post<WorkspaceSummary>("/workspaces", input);
    return data;
  },
};

export interface OnboardingData {
  name: string;
  country: string;
  currency: string;
  business_type: "registered_company" | "sole_trader" | "partnership" | "not_registered";
  industry: string;
  company_size: CompanySize;
  monthly_invoice_volume: "1-10" | "11-25" | "26-100" | "101-500" | "500+";
  accounting_software: "xero" | "quickbooks" | "sage" | "none" | "not_sure";
  invite_emails: string[];
  approver_email: string;
}

export const onboardingApi = {
  getDraft: async () => (await client.get<{ step: number; completed: boolean; data: Partial<OnboardingData> }>("/onboarding/draft")).data,
  saveDraft: async (step: number, data: Partial<OnboardingData>) =>
    (await client.put("/onboarding/draft", { step, data })).data,
  complete: async (data: OnboardingData) =>
    (await client.post<{ workspace: WorkspaceSummary }>("/onboarding/complete", data)).data.workspace,
};
