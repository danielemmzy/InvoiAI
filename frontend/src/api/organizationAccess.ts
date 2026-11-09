import { client } from "@/api/client";

export interface ApprovalAuthority {
  id: string;
  membership_id: string;
  approval_type: "invoice" | "payment";
  currency: string;
  limit_amount: number | string;
  can_self_approve: boolean;
  can_approve_exceptions: boolean;
  effective_from?: string | null;
  effective_until?: string | null;
  is_active: boolean;
}

export interface ApprovalDelegation {
  id: string;
  delegator_membership_id: string;
  delegatee_membership_id: string;
  scope: Record<string, boolean>;
  starts_at: string;
  ends_at: string;
  reason?: string | null;
}

export interface OrganizationRoleProfile {
  id: string;
  role_key: string;
  name: string;
  description?: string | null;
  permissions: string[];
  is_system: boolean;
  is_active: boolean;
}

export const organizationAccessApi = {
  authorities: async () => (await client.get<ApprovalAuthority[]>("/organization-access/authorities")).data,
  upsertAuthority: async (payload: Omit<ApprovalAuthority, "id" | "is_active">) =>
    (await client.put<ApprovalAuthority>("/organization-access/authorities", payload)).data,
  delegations: async () => (await client.get<ApprovalDelegation[]>("/organization-access/delegations")).data,
  createDelegation: async (payload: Omit<ApprovalDelegation, "id">) =>
    (await client.post<ApprovalDelegation>("/organization-access/delegations", payload)).data,
  revokeDelegation: async (id: string) =>
    (await client.post(`/organization-access/delegations/${id}/revoke`)).data,
  roles: async () => (await client.get<OrganizationRoleProfile[]>("/organization-access/roles")).data,
  sodRules: async () => (await client.get("/organization-access/sod-rules")).data,
};
