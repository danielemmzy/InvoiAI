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
