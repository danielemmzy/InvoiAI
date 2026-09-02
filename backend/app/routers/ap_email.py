from __future__ import annotations
import hashlib, hmac, json
from fastapi import APIRouter, HTTPException, Request, Response
from app.core.config import settings
from app.core.limiter import limiter
from app.core.container import get_container
from app.services.ap.email_intake_service import EmailIntakeService

router = APIRouter(prefix="/ap/email", tags=["AP Email Intake"])


@router.post("/inbound")
@limiter.limit("30/minute")
async def inbound_email(request: Request, response: Response):
    raw = await request.body()
    secret = settings.ap_email_webhook_secret
    if not secret:
        raise HTTPException(503, "AP email intake is not configured")
    supplied = request.headers.get("X-InvoiAI-Email-Signature", "")
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(401, "Invalid email webhook signature")
    try:
        body = json.loads(raw)
    except Exception as exc:
        raise HTTPException(400, "Invalid JSON payload") from exc
    try:
        return await EmailIntakeService(get_container().document_upload_service).ingest(
            to_address=body["to"],
            sender=body.get("from"),
            subject=body.get("subject"),
            message_id=body["message_id"],
            attachments=body.get("attachments", []),
            industry=body.get("industry", "general"),
            currency=body.get("currency", "USD"),
        )
    except KeyError as exc:
        raise HTTPException(400, f"Missing field: {exc.args[0]}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
