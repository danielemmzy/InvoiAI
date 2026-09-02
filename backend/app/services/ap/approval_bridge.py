from __future__ import annotations
from datetime import UTC, datetime, timedelta
from uuid import UUID
from app.core.enum.application import ApprovalStatus
from app.core.enum.database import RiskLevel
from app.core.supabase import get_supabase

class APApprovalBridge:
    def __init__(self, db=None): self.db=db or get_supabase()
    async def create_workflow(self, *, org_id: UUID, document_id: UUID, analysis_id: UUID, initiated_by: UUID | None):
        existing=self.db.table("approval_workflows").select("id").eq("org_id",str(org_id)).eq("document_id",str(document_id)).limit(1).execute()
        if existing.data: return existing.data[0]["id"]
        doc=self.db.table("documents").select("total_amount,document_type,vendor_name").eq("org_id",str(org_id)).eq("id",str(document_id)).single().execute().data
        analysis=self.db.table("document_analyses").select("risk_level").eq("org_id",str(org_id)).eq("id",str(analysis_id)).single().execute().data
        approver=self.db.table("org_members").select("user_id,role,spending_limit").eq("org_id",str(org_id)).eq("is_active",True).in_("role",["owner","admin","approver"]).order("role").limit(1).execute().data
        if not approver: raise ValueError("No active approver is configured for this organization.")
        a=approver[0]; now=datetime.now(UTC); due=now+timedelta(days=2)
        workflow=self.db.table("approval_workflows").insert({"org_id":str(org_id),"document_id":str(document_id),"analysis_id":str(analysis_id),"status":ApprovalStatus.IN_REVIEW.value,"current_step":1,"total_steps":1,"document_amount":str(doc.get("total_amount") or 0),"document_type":doc.get("document_type") or "invoice","vendor_name":doc.get("vendor_name") or "Unknown vendor","risk_level":analysis.get("risk_level") or RiskLevel.MEDIUM.value,"initiated_by":str(initiated_by or UUID(a["user_id"])),"due_date":due.isoformat(),"escalation_due":(due+timedelta(days=1)).isoformat(),"auto_approved":False,"auto_rejected":False,"is_urgent":False,"metadata":{"ap_automation":True}}).execute().data[0]
        self.db.table("approval_steps").insert({"workflow_id":workflow["id"],"org_id":str(org_id),"step_number":1,"step_name":"AP Approval","approver_id":a["user_id"],"approver_role":a["role"],"spending_limit":a.get("spending_limit"),"decision":"pending","due_date":due.isoformat()}).execute()
        self.db.table("documents").update({"status":"in_approval","pipeline_stage":"approval","ap_status":"awaiting_approval"}).eq("id",str(document_id)).eq("org_id",str(org_id)).execute()
        return workflow["id"]
    async def sync_after_decision(self, *, workflow_id: UUID, document_id: UUID, actor_id: UUID):
        workflow=self.db.table("approval_workflows").select("*").eq("id",str(workflow_id)).single().execute().data
        steps=self.db.table("approval_steps").select("decision").eq("workflow_id",str(workflow_id)).execute().data or []
        if any(s.get("decision")=="rejected" for s in steps):
            self.db.table("approval_workflows").update({"status":"rejected","completed_at":datetime.now(UTC).isoformat()}).eq("id",str(workflow_id)).execute()
            self.db.table("documents").update({"status":"rejected","ap_status":"rejected"}).eq("id",str(document_id)).execute(); return "rejected"
        if steps and all(s.get("decision")=="approved" for s in steps):
            self.db.table("approval_workflows").update({"status":"approved","completed_at":datetime.now(UTC).isoformat()}).eq("id",str(workflow_id)).execute()
            self.db.table("documents").update({"status":"approved","pipeline_stage":"complete","ap_status":"approved"}).eq("id",str(document_id)).execute(); return "approved"
        return "pending"
