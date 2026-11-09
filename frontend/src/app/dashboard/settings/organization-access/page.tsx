"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { UserPlus, UsersRound } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { membersApi, OrgMember } from "@/api/members";
import { organizationAccessApi, ApprovalAuthority, ApprovalDelegation, OrganizationRoleProfile } from "@/api/organizationAccess";

type LimitDraft = { invoice: string; payment: string; supervisorId: string };
const inviteRoles = [
  { value: "owner", label: "Owner" },
  { value: "admin", label: "Admin" },
  { value: "ap_manager", label: "Manager" },
  { value: "member", label: "Member" },
] as const;

function personLabel(member?: OrgMember) {
  return member?.invite_email || member?.user_id || "Unknown teammate";
}

function asText(value: number | string | null | undefined) {
  return value === null || value === undefined ? "" : String(value);
}

export default function OrganizationAccessPage() {
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [authorities, setAuthorities] = useState<ApprovalAuthority[]>([]);
  const [profiles, setProfiles] = useState<OrganizationRoleProfile[]>([]);
  const [delegations, setDelegations] = useState<ApprovalDelegation[]>([]);
  const [limitDrafts, setLimitDrafts] = useState<Record<string, LimitDraft>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [invite, setInvite] = useState({ email: "", role: "member" as (typeof inviteRoles)[number]["value"], department: "" });

  const reload = async () => {
    setLoading(true);
    try {
      const [nextMembers, nextAuthorities, nextDelegations, nextProfiles] = await Promise.all([
        membersApi.list(), organizationAccessApi.authorities(), organizationAccessApi.delegations(), organizationAccessApi.roles(),
      ]);
      setMembers(nextMembers);
      setAuthorities(nextAuthorities);
      setDelegations(nextDelegations);
      setProfiles(nextProfiles);
      setLimitDrafts(Object.fromEntries(nextMembers.map((member) => {
        const invoice = nextAuthorities.find((item) => item.membership_id === member.id && item.approval_type === "invoice");
        const payment = nextAuthorities.find((item) => item.membership_id === member.id && item.approval_type === "payment");
        return [member.id, {
          invoice: asText(invoice?.limit_amount ?? member.spending_limit),
          payment: asText(payment?.limit_amount ?? member.payment_approval_limit),
          supervisorId: member.supervisor_id || "",
        }];
      })));
    } catch {
      toast.error("Could not load organization settings.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void reload(); }, []);

  const profileByLegacyRole = useMemo(() => new Map(profiles.map((profile) => [profile.role_key, profile.id])), [profiles]);

  const updateRole = async (member: OrgMember, roleId: string) => {
    setSaving(member.id);
    try {
      await membersApi.changeAccessRole(member.id, roleId);
      toast.success("Access role updated.");
      await reload();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not update this role.");
    } finally {
      setSaving(null);
    }
  };

  const updateLimits = async (member: OrgMember) => {
    const draft = limitDrafts[member.id] || { invoice: "", payment: "", supervisorId: "" };
    const invoice = draft.invoice.trim() === "" ? null : Number(draft.invoice);
    const payment = draft.payment.trim() === "" ? null : Number(draft.payment);
    if ((invoice !== null && (!Number.isFinite(invoice) || invoice < 0)) || (payment !== null && (!Number.isFinite(payment) || payment < 0))) {
      toast.error("Approval limits must be positive numbers.");
      return;
    }
    setSaving(`${member.id}:limits`);
    try {
      await membersApi.setApprovalLimits(member.id, {
        spending_limit: invoice,
        payment_approval_limit: payment,
        supervisor_id: draft.supervisorId || null,
      });
      toast.success("Approval authority updated.");
      await reload();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not update approval authority.");
    } finally {
      setSaving(null);
    }
  };

  const inviteMember = async (event: FormEvent) => {
    event.preventDefault();
    if (!invite.email.trim()) return;
    setSaving("invite");
    try {
      await membersApi.invite({ email: invite.email.trim(), role: invite.role, department: invite.department.trim() || undefined });
      toast.success(`Invitation prepared for ${invite.email.trim()}.`);
      setInvite({ email: "", role: "member", department: "" });
      await reload();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not invite this teammate.");
    } finally {
      setSaving(null);
    }
  };

  const revokeDelegation = async (delegationId: string) => {
    setSaving(`delegation:${delegationId}`);
    try {
      await organizationAccessApi.revokeDelegation(delegationId);
      toast.success("Delegation revoked.");
      await reload();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not revoke the delegation.");
    } finally {
      setSaving(null);
    }
  };

  return <DashboardLayout>
    <div className="dash-page-header">
      <div className="section-label">Organization</div>
      <div className="dash-title serif">People & approval authority</div>
      <div className="dash-subtitle">Give each person the right access, then set separate limits for bill and payment approvals.</div>
    </div>

    <div className="card" style={{ marginBottom: 18 }}>
      <div className="card-header"><span className="card-title"><UserPlus size={16} style={{ marginRight: 8, verticalAlign: "-2px" }} />Invite a teammate</span></div>
      <form onSubmit={inviteMember} style={{ padding: 18, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10 }}>
        <input aria-label="Email address" type="email" required placeholder="teammate@company.com" value={invite.email} onChange={(event) => setInvite({ ...invite, email: event.target.value })} />
        <select aria-label="Role" value={invite.role} onChange={(event) => setInvite({ ...invite, role: event.target.value as (typeof inviteRoles)[number]["value"] })}>
          {inviteRoles.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
        </select>
        <input aria-label="Department" placeholder="Department (optional)" value={invite.department} onChange={(event) => setInvite({ ...invite, department: event.target.value })} />
        <button className="btn-primary" type="submit" disabled={saving === "invite"}>{saving === "invite" ? "Inviting…" : "Invite"}</button>
      </form>
      <div className="settings-sub" style={{ padding: "0 18px 18px" }}>Keep roles simple. Approval limits are managed separately below.</div>
    </div>

    <div className="card" style={{ marginBottom: 18 }}>
      <div className="card-header"><span className="card-title"><UsersRound size={16} style={{ marginRight: 8, verticalAlign: "-2px" }} />Access profiles</span></div>
      <div style={{ padding: 18, display: "grid", gap: 10 }}>
        {profiles.map((profile) => <div key={profile.id} style={{ display: "flex", justifyContent: "space-between", gap: 16 }}><strong>{profile.name}</strong><span className="settings-sub">{profile.description || `${profile.permissions.length} permissions`}</span></div>)}
        {!profiles.length && <span className="settings-sub">The built-in owner, admin, manager, and member roles are active.</span>}
      </div>
    </div>

    <div className="card" style={{ marginBottom: 18 }}>
      <div className="card-header"><span className="card-title">Active approval delegations</span></div>
      <div style={{ padding: 18, display: "grid", gap: 10 }}>
        {delegations.map((delegation) => <div key={delegation.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}><span>{personLabel(members.find((member) => member.id === delegation.delegator_membership_id))} → {personLabel(members.find((member) => member.id === delegation.delegatee_membership_id))}</span><span style={{ display: "flex", alignItems: "center", gap: 10 }}><span className="settings-sub">{new Date(delegation.starts_at).toLocaleDateString()} – {new Date(delegation.ends_at).toLocaleDateString()}</span><button type="button" className="btn-secondary" onClick={() => void revokeDelegation(delegation.id)} disabled={saving === `delegation:${delegation.id}`}>Revoke</button></span></div>)}
        {!delegations.length && <span className="settings-sub">No active delegations.</span>}
      </div>
    </div>

    <div className="card">
      <div className="card-header"><span className="card-title">Team & approval authority</span></div>
      {loading ? <div style={{ padding: 20 }}>Loading your team…</div> : members.map((member) => {
        const draft = limitDrafts[member.id] || { invoice: "", payment: "", supervisorId: "" };
        const selectedRole = member.access_role_id || profileByLegacyRole.get(member.role) || "";
        return <div key={member.id} style={{ padding: 18, borderBottom: "1px solid #eee", display: "grid", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <div><strong>{personLabel(member)}</strong><div className="settings-sub">{member.department || "No department"} · {member.is_active ? "Active" : "Invitation pending"}</div></div>
            {profiles.length ? <select aria-label={`Access role for ${personLabel(member)}`} value={selectedRole} disabled={saving === member.id} onChange={(event) => void updateRole(member, event.target.value)}>{profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}</select> : <span className="settings-sub">{member.role}</span>}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10, alignItems: "end" }}>
            <label className="settings-sub">Bill approval limit<input aria-label={`Bill approval limit for ${personLabel(member)}`} inputMode="decimal" placeholder="Not configured" value={draft.invoice} onChange={(event) => setLimitDrafts({ ...limitDrafts, [member.id]: { ...draft, invoice: event.target.value } })} /></label>
            <label className="settings-sub">Payment approval limit<input aria-label={`Payment approval limit for ${personLabel(member)}`} inputMode="decimal" placeholder="Not configured" value={draft.payment} onChange={(event) => setLimitDrafts({ ...limitDrafts, [member.id]: { ...draft, payment: event.target.value } })} /></label>
            <label className="settings-sub">Escalate to<select aria-label={`Supervisor for ${personLabel(member)}`} value={draft.supervisorId} onChange={(event) => setLimitDrafts({ ...limitDrafts, [member.id]: { ...draft, supervisorId: event.target.value } })}><option value="">No escalation</option>{members.filter((candidate) => candidate.id !== member.id && candidate.is_active).map((candidate) => <option key={candidate.id} value={candidate.id}>{personLabel(candidate)}</option>)}</select></label>
            <button type="button" className="btn-secondary" onClick={() => void updateLimits(member)} disabled={saving === `${member.id}:limits`}>{saving === `${member.id}:limits` ? "Saving…" : "Save limits"}</button>
          </div>
        </div>;
      })}
    </div>
  </DashboardLayout>;
}
