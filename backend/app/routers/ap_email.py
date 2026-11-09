from __future__ import annotations
import hashlib, hmac, json, time
from fastapi import APIRouter, HTTPException, Request, Response
from app.core.config import settings
from app.core.limiter import limiter
from app.core.container import get_container
from app.services.ap.email_intake_service import EmailIntakeService

router = APIRouter(prefix="/ap/email", tags=["AP Email Intake"])
MAX_MESSAGE_BYTES = 32 * 1024 * 1024
SIGNATURE_TOLERANCE_SECONDS = 300


def valid_webhook_signature(raw: bytes, signature: str, timestamp: str, *, now: int | None = None) -> bool:
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs((int(time.time()) if now is None else now) - sent_at) > SIGNATURE_TOLERANCE_SECONDS:
        return False
    # Provider-neutral adapter contract: sign the timestamp and exact payload bytes.
    expected = hmac.new(settings.ap_email_webhook_secret.encode(), timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


@router.post("/inbound")
@limiter.limit("30/minute")
async def inbound_email(request: Request, response: Response):
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_MESSAGE_BYTES:
        raise HTTPException(413, "Email message exceeds 32 MB.")
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_MESSAGE_BYTES:
            raise HTTPException(413, "Email message exceeds 32 MB.")
        chunks.append(chunk)
    raw = b"".join(chunks)
    secret = settings.ap_email_webhook_secret
    if not secret:
        raise HTTPException(503, "AP email intake is not configured")
    supplied = request.headers.get("X-InvoiAI-Email-Signature", "")
    timestamp = request.headers.get("X-InvoiAI-Email-Timestamp", "")
    if not valid_webhook_signature(raw, supplied, timestamp):
        raise HTTPException(401, "Invalid or expired email webhook signature")
    try:
        body = json.loads(raw)
    except Exception as exc:
        raise HTTPException(400, "Invalid JSON payload") from exc
    if not isinstance(body, dict):
        raise HTTPException(400, "Email webhook payload must be a JSON object")
    try:
        return await EmailIntakeService(get_container().document_upload_service).ingest(
            to_address=body["to"],
            sender=body.get("from"),
            subject=body.get("subject"),
            message_id=body["message_id"],
            attachments=body.get("attachments", []),
            auth_results=body.get("auth_results", {}),
            industry=body.get("industry", "general"),
            currency=body.get("currency", "USD"),
        )
    except KeyError as exc:
        raise HTTPException(400, f"Missing field: {exc.args[0]}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
