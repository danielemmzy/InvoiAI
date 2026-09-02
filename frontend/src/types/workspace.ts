export type WorkspaceType = "personal" | "business";

// Mirrors schemas/workspace.py CompanySize exactly.
export type CompanySize = "1" | "2-10" | "11-50" | "51-200" | "201-500" | "500+";

export interface WorkspaceSummary {
  id: string;
  name: string;
  slug: string;
  type: WorkspaceType;
  role: string;
  plan: string;
  currency: string;
  created_at: string;
}
