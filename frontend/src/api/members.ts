import { client } from "@/api/client";

export interface OrgMember {
  id: string;
  org_id: string;
  user_id: string;
  role: string;
  access_role_id?: string | null;
  department?: string | null;
  cost_center?: string | null;
  spending_limit?: number | null;
  payment_approval_limit?: number | null;
  supervisor_id?: string | null;
  invite_email?: string | null;
  is_active: boolean;
  joined_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface InviteMemberInput {
  email: string;
  role: "admin" | "ap_member" | "approver";
  department?: string;
  spending_limit?: number;
}

export interface ApprovalLimitsInput {
  spending_limit?: number | null;
  payment_approval_limit?: number | null;
  supervisor_id?: string | null;
}

export const membersApi = {
  list: async () => (await client.get<OrgMember[]>("/members")).data,
  changeRole: async (membershipId: string, role: string) =>
    (await client.patch<OrgMember>(`/members/${membershipId}/role`, { role })).data,
  changeAccessRole: async (membershipId: string, roleId: string) =>
    (await client.patch<OrgMember>(`/members/${membershipId}/access-role/${roleId}`)).data,
  invite: async (payload: InviteMemberInput) =>
    (await client.post<{ membership_id: string; invite_email: string; status: string }>("/members/invite", payload)).data,
  setApprovalLimits: async (membershipId: string, payload: ApprovalLimitsInput) =>
    (await client.patch<OrgMember>(`/members/${membershipId}/approval-limits`, payload)).data,
  remove: async (membershipId: string) =>
    (await client.delete<{ status: string }>(`/members/${membershipId}`)).data,
};
