"use client";
// AP automation settings — /dashboard/settings/ap-rules
// Conditional approval routing rules for bills and payments.
// Rules are evaluated in priority order by APRoutingEngine
// (app/services/ap/routing_engine.py); this page is the "editable
// without developer intervention" surface for them.

import { useState } from "react";
import Link from "next/link";
import { Plus, Trash2, Loader2 } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { PageLoading, PageError, EmptyState } from "@/components/ui/PageState";
import {
  useApprovalRules, useCreateApprovalRule, useDeleteApprovalRule,
  useApprovalGroups, useCreateApprovalGroup, useGroupMembers, useAddGroupMember, useRemoveGroupMember,
  useOrgMembers, useSetMemberApprovalLimits,
} from "@/hooks/useAP";
import type { OrgMember } from "@/api/members";
import type { ApprovalRuleScope, ApprovalExecutionMode, ApproverType, ApprovalRuleCreate } from "@/api/ap";

const EXECUTION_MODES: ApprovalExecutionMode[] = ["sequential", "parallel", "any_one", "group"];
const APPROVER_TYPES: ApproverType[] = ["role", "user", "group"];
const ROLE_OPTIONS = ["owner", "admin", "approver", "ap_member", "member"];

function emptyDraft(scope: ApprovalRuleScope): ApprovalRuleCreate {
  return {
    name: "", description: "", is_active: true, priority: 100, scope,
    min_amount: null, max_amount: null, vendor_id: null, department: null,
    cost_center: null, location: null, document_type: null, risk_level: null,
    requires_po: null, step_number: 1, step_name: "Approval",
    execution_mode: "sequential", approver_type: "role",
    approver_id: null, approver_role: "approver", approver_group_id: null,
    conditions: null, actions: null,
  };
}

function NewRuleForm({ scope, groups, members, onClose }: { scope: ApprovalRuleScope; groups: { id: string; name: string }[]; members: OrgMember[]; onClose: () => void }) {
  const [draft, setDraft] = useState<ApprovalRuleCreate>(emptyDraft(scope));
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [conditionsText, setConditionsText] = useState("");
  const [actionsText, setActionsText] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const create = useCreateApprovalRule();

  const set = <K extends keyof ApprovalRuleCreate>(key: K, value: ApprovalRuleCreate[K]) =>
    setDraft((d) => ({ ...d, [key]: value }));

  const submit = () => {
    let conditions: ApprovalRuleCreate["conditions"] = null;
    let actions: ApprovalRuleCreate["actions"] = null;
    try {
      if (conditionsText.trim()) conditions = JSON.parse(conditionsText);
      if (actionsText.trim()) actions = JSON.parse(actionsText);
    } catch {
      setJsonError("Conditions and actions must be valid JSON.");
      return;
    }
    setJsonError(null);
    create.mutate({ ...draft, conditions, actions }, { onSuccess: onClose });
  };

  return (
    <div className="panel" style={{ marginBottom: 18 }}>
      <div className="panel-head">
        <div>
          <div className="panel-kicker">New {scope} rule</div>
          <h2>Conditions &amp; approver</h2>
        </div>
      </div>

      <div className="rule-form-grid">
        <label>Name
          <input value={draft.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. High-value IT purchases" />
        </label>
        <label>Priority (lower runs first)
          <input type="number" value={draft.priority} onChange={(e) => set("priority", Number(e.target.value))} />
        </label>
        <label>Min amount
          <input type="number" value={draft.min_amount ?? ""} onChange={(e) => set("min_amount", e.target.value ? Number(e.target.value) : null)} />
        </label>
        <label>Max amount
          <input type="number" value={draft.max_amount ?? ""} onChange={(e) => set("max_amount", e.target.value ? Number(e.target.value) : null)} />
        </label>
        <label>Department
          <input value={draft.department ?? ""} onChange={(e) => set("department", e.target.value || null)} placeholder="Any" />
        </label>
        <label>Location
          <input value={draft.location ?? ""} onChange={(e) => set("location", e.target.value || null)} placeholder="Any" />
        </label>
        <label>Step name
          <input value={draft.step_name} onChange={(e) => set("step_name", e.target.value)} />
        </label>
        <label>Execution mode
          <select value={draft.execution_mode} onChange={(e) => set("execution_mode", e.target.value as ApprovalExecutionMode)}>
            {EXECUTION_MODES.map((m) => <option key={m} value={m}>{m.replace("_", "-")}</option>)}
          </select>
        </label>
        <label>Approver type
          <select value={draft.approver_type} onChange={(e) => set("approver_type", e.target.value as ApproverType)}>
            {APPROVER_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        {draft.approver_type === "role" && (
          <label>Approver role
            <select value={draft.approver_role ?? "approver"} onChange={(e) => set("approver_role", e.target.value)}>
              {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
        )}
        {draft.approver_type === "user" && (
          <label>Approver user ID
            <select value={draft.approver_id ?? ""} onChange={(e) => set("approver_id", e.target.value || null)}>
              <option value="">Select an active approver…</option>
              {members.filter((member) => member.is_active && member.role === "approver").map((member) => <option key={member.id} value={member.user_id}>{member.invite_email ?? member.user_id}</option>)}
            </select>
          </label>
        )}
        {draft.approver_type === "group" && (
          <label>Approver group
            <select value={draft.approver_group_id ?? ""} onChange={(e) => set("approver_group_id", e.target.value || null)}>
              <option value="">Select a group…</option>
              {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          </label>
        )}
      </div>

      <button
        type="button"
        className="btn-quiet"
        style={{ marginTop: 14, padding: 0, fontSize: 12 }}
        onClick={() => setShowAdvanced((s) => !s)}
      >
        {showAdvanced ? "Hide advanced (conditions / actions JSON)" : "Advanced: conditions / actions (JSON)"}
      </button>

      {showAdvanced && (
        <div className="rule-form-grid" style={{ marginTop: 10, gridTemplateColumns: "1fr 1fr" }}>
          <label>Conditions tree (overrides amount/department/etc. above when set)
            <textarea
              className="modal-textarea"
              rows={6}
              placeholder={'{"op":"and","conditions":[{"field":"amount","op":"gt","value":5000},{"field":"department","op":"eq","value":"IT"}]}'}
              value={conditionsText}
              onChange={(e) => setConditionsText(e.target.value)}
            />
          </label>
          <label>Actions (overrides the single approver above when set)
            <textarea
              className="modal-textarea"
              rows={6}
              placeholder={'[{"type":"add_approver","approver_type":"role","approver_role":"finance_manager"},{"type":"escalate","approver_type":"role","approver_role":"finance_manager"}]'}
              value={actionsText}
              onChange={(e) => setActionsText(e.target.value)}
            />
          </label>
        </div>
      )}
      {jsonError && <p style={{ color: "#C0392B", fontSize: 12.5, marginTop: 8 }}>{jsonError}</p>}

      <div className="drawer-actions" style={{ marginTop: 16 }}>
        <button className="btn-secondary" onClick={onClose}>Cancel</button>
        <button
          className="btn-primary"
          disabled={!draft.name.trim() || create.isPending}
          onClick={submit}
        >
          {create.isPending ? <Loader2 size={14} className="spin" /> : "Create rule"}
        </button>
      </div>
    </div>
  );
}

function RulesTable({ scope }: { scope: ApprovalRuleScope }) {
  const rules = useApprovalRules(scope);
  const groups = useApprovalGroups();
  const members = useOrgMembers();
  const del = useDeleteApprovalRule();
  const [showForm, setShowForm] = useState(false);

  const columns = "1.4fr 0.8fr 1fr 1fr 1fr 0.6fr";

  return (
    <div>
      <div className="panel-head" style={{ marginBottom: 10 }}>
        <div />
        <button className="btn-secondary" onClick={() => setShowForm((s) => !s)}>
          <Plus size={14} /> New rule
        </button>
      </div>

      {showForm && (
        <NewRuleForm scope={scope} groups={groups.data ?? []} members={members.data ?? []} onClose={() => setShowForm(false)} />
      )}

      {rules.isLoading ? (
        <PageLoading variant="table" />
      ) : rules.isError ? (
        <PageError onRetry={rules.refetch} />
      ) : !rules.data?.length ? (
        <EmptyState
          title={`No ${scope} rules yet`}
          message={`Without a rule, ${scope} approvals fall back to the first active owner/admin/approver in the org.`}
        />
      ) : (
        <div className="ap-table">
          <div className="ap-table-head" style={{ gridTemplateColumns: columns }}>
            <span>Name</span><span>Priority</span><span>Amount range</span>
            <span>Mode</span><span>Approver</span><span />
          </div>
          {rules.data.map((r) => (
            <div key={r.id} className="ap-table-row" style={{ gridTemplateColumns: columns, cursor: "default" }}>
              <span className="ap-table-vendor">{r.name}{!r.is_active && <span className="status-pill neutral" style={{ marginLeft: 6 }}>Inactive</span>}</span>
              <span>{r.priority}</span>
              <span>{r.min_amount != null ? `$${r.min_amount}` : "any"} – {r.max_amount != null ? `$${r.max_amount}` : "any"}</span>
              <span>{r.execution_mode.replace("_", "-")}</span>
              <span>{r.approver_type === "role" ? r.approver_role : r.approver_type === "group" ? "Group" : "User"}</span>
              <span style={{ display: "flex", justifyContent: "flex-end" }}>
                <button className="btn-quiet" title="Delete rule" onClick={() => del.mutate(r.id)}>
                  <Trash2 size={14} />
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function GroupMembersRow({ groupId }: { groupId: string }) {
  const members = useGroupMembers(groupId);
  const orgMembers = useOrgMembers();
  const addMember = useAddGroupMember();
  const removeMember = useRemoveGroupMember();
  const [selected, setSelected] = useState("");

  const memberUserIds = new Set((members.data ?? []).map((m) => m.user_id));
  const availableMembers = (orgMembers.data ?? []).filter((m) => !memberUserIds.has(m.user_id));

  return (
    <div style={{ padding: "12px 0 16px", borderTop: "1px solid #EBE6DC" }}>
      {members.isLoading ? (
        <PageLoading variant="cards" />
      ) : !members.data?.length ? (
        <p className="muted">No members yet — add one below.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: "0 0 12px", display: "flex", flexWrap: "wrap", gap: 8 }}>
          {members.data.map((m) => {
            const orgMember = orgMembers.data?.find((om) => om.user_id === m.user_id);
            return (
              <li key={m.id} className="status-pill neutral" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {orgMember?.invite_email ?? m.user_id.slice(0, 8)}
                <button
                  className="btn-quiet"
                  style={{ padding: 0 }}
                  title="Remove from group"
                  onClick={() => removeMember.mutate({ groupId, userId: m.user_id })}
                >
                  <Trash2 size={12} />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <div style={{ display: "flex", gap: 8 }}>
        <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ flex: 1 }}>
          <option value="">Add a member…</option>
          {availableMembers.map((m) => (
            <option key={m.user_id} value={m.user_id}>{m.invite_email ?? m.user_id}</option>
          ))}
        </select>
        <button
          className="btn-secondary"
          disabled={!selected || addMember.isPending}
          onClick={() => addMember.mutate({ groupId, userId: selected }, { onSuccess: () => setSelected("") })}
        >
          <Plus size={14} /> Add
        </button>
      </div>
    </div>
  );
}

function GroupsPanel() {
  const groups = useApprovalGroups();
  const create = useCreateApprovalGroup();
  const [name, setName] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <div className="panel-kicker">Approval groups</div>
          <h2>Pooled approvers</h2>
          <p>A processing group — first eligible member to claim a task decides it.</p>
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. AP Processing Team"
          style={{ flex: 1 }}
        />
        <button
          className="btn-secondary"
          disabled={!name.trim() || create.isPending}
          onClick={() => create.mutate({ name: name.trim() }, { onSuccess: () => setName("") })}
        >
          <Plus size={14} /> Add group
        </button>
      </div>

      {groups.isLoading ? (
        <PageLoading variant="cards" />
      ) : !groups.data?.length ? (
        <EmptyState title="No groups yet" message="Create a group above, then add members to it." />
      ) : (
        <ul className="modal-reason-list" style={{ paddingLeft: 0, listStyle: "none" }}>
          {groups.data.map((g) => (
            <li key={g.id} style={{ padding: "8px 0", borderTop: "1px solid #EBE6DC" }}>
              <button
                className="btn-quiet"
                style={{ display: "flex", justifyContent: "space-between", width: "100%", padding: "4px 0" }}
                onClick={() => setExpanded(expanded === g.id ? null : g.id)}
              >
                <span><strong>{g.name}</strong>{g.description ? ` — ${g.description}` : ""}</span>
                <span className="muted">{expanded === g.id ? "Hide members" : "Manage members"}</span>
              </button>
              {expanded === g.id && <GroupMembersRow groupId={g.id} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function ApRulesSettingsPage() {
  const [scope, setScope] = useState<ApprovalRuleScope>("bill");

  return (
    <DashboardLayout>
      <div className="dash-page-header">
        <div className="section-label">§04 Account / Settings</div>
        <div className="dash-title serif">AP automation</div>
        <div className="dash-subtitle">
          Conditional approval routing, pooled approver groups, and payment controls — evaluated by the AP routing
          engine in priority order. <Link href="/dashboard/ap/payments">View payment queue →</Link>
        </div>
      </div>

      <div className="ap-subnav" style={{ marginBottom: 18, display: "inline-flex" }}>
        <button className={`ap-subnav-item ${scope === "bill" ? "active" : ""}`} onClick={() => setScope("bill")} style={{ border: 0, cursor: "pointer" }}>
          Bill approval rules
        </button>
        <button className={`ap-subnav-item ${scope === "payment" ? "active" : ""}`} onClick={() => setScope("payment")} style={{ border: 0, cursor: "pointer" }}>
          Payment approval rules
        </button>
      </div>

      <RulesTable scope={scope} />

      <div style={{ marginTop: 24 }}>
        <GroupsPanel />
      </div>

      <div style={{ marginTop: 24 }}>
        <MemberLimitsPanel />
      </div>
    </DashboardLayout>
  );
}

function MemberLimitsPanel() {
  const members = useOrgMembers();
  const setLimits = useSetMemberApprovalLimits();
  const [drafts, setDrafts] = useState<Record<string, { spending_limit: string; payment_approval_limit: string; supervisor_id: string }>>({});

  const draftFor = (m: OrgMember) =>
    drafts[m.id] ?? {
      spending_limit: m.spending_limit != null ? String(m.spending_limit) : "",
      payment_approval_limit: m.payment_approval_limit != null ? String(m.payment_approval_limit) : "",
      supervisor_id: m.supervisor_id ?? "",
    };

  const setDraft = (id: string, patch: Partial<{ spending_limit: string; payment_approval_limit: string; supervisor_id: string }>) =>
    setDrafts((d) => ({ ...d, [id]: { ...draftFor(members.data!.find((m) => m.id === id)!), ...d[id], ...patch } }));

  const columns = "1.4fr 1fr 1fr 1fr 0.6fr";

  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <div className="panel-kicker">Approval limits</div>
          <h2>Bill &amp; payment limits, supervisor escalation</h2>
          <p>
            Leave a limit blank for unlimited authority. Above a member&apos;s limit, the routing engine
            automatically escalates to their supervisor.
          </p>
        </div>
      </div>

      {members.isLoading ? (
        <PageLoading variant="table" />
      ) : !members.data?.length ? (
        <EmptyState title="No members yet" />
      ) : (
        <div className="ap-table">
          <div className="ap-table-head" style={{ gridTemplateColumns: columns }}>
            <span>Member</span><span>Bill limit</span><span>Payment limit</span><span>Supervisor</span><span />
          </div>
          {members.data.map((m) => {
            const d = draftFor(m);
            const otherMembers = members.data!.filter((om) => om.id !== m.id);
            return (
              <div key={m.id} className="ap-table-row" style={{ gridTemplateColumns: columns, cursor: "default" }}>
                <span className="ap-table-vendor">{m.invite_email ?? m.user_id.slice(0, 8)} <span className="muted">· {m.role}</span></span>
                <span>
                  <input
                    type="number"
                    value={d.spending_limit}
                    onChange={(e) => setDraft(m.id, { spending_limit: e.target.value })}
                    placeholder="Unlimited"
                    style={{ width: "100%" }}
                  />
                </span>
                <span>
                  <input
                    type="number"
                    value={d.payment_approval_limit}
                    onChange={(e) => setDraft(m.id, { payment_approval_limit: e.target.value })}
                    placeholder="Unlimited"
                    style={{ width: "100%" }}
                  />
                </span>
                <span>
                  <select value={d.supervisor_id} onChange={(e) => setDraft(m.id, { supervisor_id: e.target.value })} style={{ width: "100%" }}>
                    <option value="">None</option>
                    {otherMembers.map((om) => (
                      <option key={om.id} value={om.id}>{om.invite_email ?? om.user_id.slice(0, 8)}</option>
                    ))}
                  </select>
                </span>
                <span>
                  <button
                    className="btn-secondary"
                    disabled={setLimits.isPending}
                    onClick={() =>
                      setLimits.mutate({
                        membershipId: m.id,
                        payload: {
                          spending_limit: d.spending_limit ? Number(d.spending_limit) : null,
                          payment_approval_limit: d.payment_approval_limit ? Number(d.payment_approval_limit) : null,
                          supervisor_id: d.supervisor_id || null,
                        },
                      })
                    }
                  >
                    Save
                  </button>
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
