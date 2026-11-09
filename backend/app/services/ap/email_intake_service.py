from __future__ import annotations

import base64
import binascii
import hashlib
from uuid import UUID

from app.core.supabase import get_supabase
from app.core.enum.database import DocumentType
from app.services.document.document_upload_service import DocumentUploadService

MAX_ATTACHMENTS = 25
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/tiff"}

class EmailIntakeService:
    """Retry-safe email ingestion. Each attachment has a durable unique key so a
    partially failed message can resume without re-uploading completed files.
    Apply 20261010_ap_email_intake_idempotency.sql before enabling this service.
    """
    def __init__(self, upload_service: DocumentUploadService, db=None):
        self.upload = upload_service
        self.db = db or get_supabase()

    async def ingest(self, *, to_address: str, sender: str | None, subject: str | None,
                     message_id: str, attachments: list[dict], industry="general", currency="USD"):
        if not message_id or len(message_id) > 998:
            raise ValueError("A valid provider message ID is required.")
        if not attachments or len(attachments) > MAX_ATTACHMENTS:
            raise ValueError(f"Email must contain between 1 and {MAX_ATTACHMENTS} attachments.")
        rows = self.db.table("ap_email_intake_addresses").select("*").eq(
            "email_address", to_address.lower().strip()).eq("is_active", True).limit(1).execute().data
        if not rows:
            raise ValueError("Unknown or inactive InvoiAI intake address.")
        address = rows[0]; org_id = UUID(address["org_id"])
        event_rows = self.db.table("ap_email_intake_events").select("id,processed").eq(
            "intake_address_id", address["id"]).eq("provider_message_id", message_id).limit(1).execute().data or []
        if event_rows:
            event = event_rows[0]
            if event.get("processed"):
                return {"duplicate": True, "documents": []}
        else:
            event = self.db.table("ap_email_intake_events").insert({
                "org_id": str(org_id), "intake_address_id": address["id"],
                "provider_message_id": message_id, "sender_email": sender, "subject": subject,
                "attachment_count": len(attachments), "metadata": {}, "processed": False,
            }).execute().data[0]
        docs = []
        try:
            for index, attachment in enumerate(attachments):
                try:
                    content = base64.b64decode(attachment["content_base64"], validate=True)
                except (KeyError, ValueError, binascii.Error) as exc:
                    raise ValueError(f"Attachment {index + 1} has invalid base64 content.") from exc
                if not content or len(content) > MAX_ATTACHMENT_BYTES:
                    raise ValueError(f"Attachment {index + 1} is empty or exceeds 25 MB.")
                filename = (attachment.get("filename") or f"email-attachment-{index + 1}.pdf").replace("\\", "/").split("/")[-1]
                content_type = (attachment.get("content_type") or "").split(";")[0].strip().lower()
                if not content_type or content_type == "application/octet-stream":
                    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
                    content_type = {"pdf":"application/pdf", "png":"image/png", "jpg":"image/jpeg", "jpeg":"image/jpeg", "tif":"image/tiff", "tiff":"image/tiff"}.get(ext, "")
                signatures = {"application/pdf": content.startswith(b"%PDF-"), "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"), "image/jpeg": content.startswith(b"\xff\xd8\xff"), "image/tiff": content.startswith((b"II*\x00", b"MM\x00*"))}
                if content_type not in ALLOWED_TYPES or not signatures.get(content_type, False):
                    raise ValueError(f"Attachment '{filename}' is not a supported file or its signature does not match.")
                digest = hashlib.sha256(content).hexdigest()
                key = hashlib.sha256(f"{address['id']}:{message_id}:{index}:{digest}".encode()).hexdigest()
                prior = self.db.table("ap_email_intake_attachments").select("document_id,status").eq("idempotency_key", key).limit(1).execute().data or []
                if prior and prior[0].get("status") == "processed":
                    if prior[0].get("document_id"): docs.append(prior[0]["document_id"])
                    continue
                if not prior:
                    self.db.table("ap_email_intake_attachments").insert({
                        "org_id": str(org_id), "event_id": event["id"], "attachment_index": index,
                        "filename": filename, "content_sha256": digest, "idempotency_key": key, "status": "processing"
                    }).execute()
                doc = await self.upload.upload(org_id=org_id, user_id=UUID(address["created_by"]) if address.get("created_by") else None,
                    filename=filename, content_type=content_type, content=content, industry=industry,
                    document_type=DocumentType.INVOICE, currency=currency, source_override="email_forward",
                    external_metadata={"email_message_id": message_id, "sender": sender, "subject": subject})
                doc_id = str(doc.id)
                self.db.table("ap_email_intake_attachments").update({"status":"processed", "document_id":doc_id, "processed_at":"now()"}).eq("idempotency_key", key).execute()
                docs.append(doc_id)
            self.db.table("ap_email_intake_events").update({"processed": True, "processed_at": "now()", "error_message": None}).eq("id", event["id"]).execute()
            return {"duplicate": False, "documents": docs}
        except Exception as exc:
            self.db.table("ap_email_intake_events").update({"processed": False, "error_message": str(exc)[:1000]}).eq("id", event["id"]).execute()
            raise
