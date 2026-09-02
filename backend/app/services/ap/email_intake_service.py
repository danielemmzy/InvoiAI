from __future__ import annotations
import base64
from uuid import UUID
from app.core.supabase import get_supabase
from app.core.enum.database import DocumentType
from app.services.document.document_upload_service import DocumentUploadService

class EmailIntakeService:
    def __init__(self, upload_service: DocumentUploadService, db=None): self.upload=upload_service; self.db=db or get_supabase()
    async def ingest(self, *, to_address: str, sender: str|None, subject: str|None, message_id: str, attachments: list[dict], industry="general", currency="USD"):
        address=self.db.table("ap_email_intake_addresses").select("*").eq("email_address",to_address.lower().strip()).eq("is_active",True).limit(1).execute().data
        if not address: raise ValueError("Unknown or inactive InvoiAI intake address.")
        a=address[0]; org_id=UUID(a["org_id"])
        existing=self.db.table("ap_email_intake_events").select("id,processed").eq("intake_address_id",a["id"]).eq("provider_message_id",message_id).limit(1).execute().data
        if existing: return {"duplicate":True,"documents":[]}
        event=self.db.table("ap_email_intake_events").insert({"org_id":str(org_id),"intake_address_id":a["id"],"provider_message_id":message_id,"sender_email":sender,"subject":subject,"attachment_count":len(attachments),"metadata":{}}).execute().data[0]
        docs=[]
        try:
            for attachment in attachments:
                content=base64.b64decode(attachment["content_base64"])
                content_type=attachment.get("content_type") or "application/pdf"
                doc=await self.upload.upload(org_id=org_id,user_id=UUID(a["created_by"]) if a.get("created_by") else None,filename=attachment.get("filename") or "email-attachment.pdf",content_type=content_type,content=content,industry=industry,document_type=DocumentType.INVOICE,currency=currency,source_override="email_forward",external_metadata={"email_message_id":message_id,"sender":sender,"subject":subject})
                docs.append(str(doc.id))
            self.db.table("ap_email_intake_events").update({"processed":True,"processed_at":"now()"}).eq("id",event["id"]).execute()
            return {"duplicate":False,"documents":docs}
        except Exception as exc:
            self.db.table("ap_email_intake_events").update({"error_message":str(exc)}).eq("id",event["id"]).execute()
            raise
