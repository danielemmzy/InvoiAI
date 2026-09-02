"""
============================================================
Integration Webhooks Router

Mounts app/webhooks/{quickbooks,xero,google}.py, which existed
fully implemented (signature verification, payload parsing)
but had no HTTP route pointing at them — only Stripe's webhook
had a registered router. Flow 5's "Path B: WEBHOOK-TRIGGERED"
was unreachable until now.

POST /api/v1/webhooks/quickbooks
POST /api/v1/webhooks/xero
POST /api/v1/webhooks/google
POST /api/v2/webhooks/stripe
============================================================
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.webhooks.google import GoogleWebhookHandler
from app.webhooks.quickbooks import QuickBooksWebhookHandler
from app.webhooks.stripe import StripeWebhookHandler
from app.webhooks.webhook_dispatcher import WebhookDispatcher
from app.webhooks.xero import XeroWebhookHandler

router = APIRouter(prefix="/webhooks", tags=["Integration Webhooks"])


async def _handle(request: Request, handler) -> dict:
    body = await request.body()
    headers = dict(request.headers)

    verified = await handler.verify(headers=headers, body=body)
    if not verified:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = await request.json()
    events = await handler.parse(payload=payload)

    dispatcher = WebhookDispatcher()
    for event in events:
        await dispatcher.dispatch(event=event)

    return {"received": True, "events_processed": len(events)}


@router.post("/quickbooks")
async def quickbooks_webhook(request: Request):
    return await _handle(request, QuickBooksWebhookHandler())


@router.post("/xero")
async def xero_webhook(request: Request):
    return await _handle(request, XeroWebhookHandler())


@router.post("/google")
async def google_webhook(request: Request):
    return await _handle(request, GoogleWebhookHandler())


@router.post("/stripe")
async def stripe_webhook(request: Request):
    return await _handle(request, StripeWebhookHandler())
