# AP email intake integration boundary

`POST /api/v2/ap/email/inbound` accepts a provider-neutral JSON webhook. The sender must sign the exact request bytes with HMAC-SHA256 over `{timestamp}.{body}` using `AP_EMAIL_WEBHOOK_SECRET`, and send the Unix timestamp in `X-InvoiAI-Email-Timestamp`. Timestamps older than five minutes are rejected. The signed payload must contain one exact `to` address, a stable `message_id`, attachment content in base64, and provider-derived `auth_results` for SPF, DKIM, and DMARC.

The application does not connect to an inbound email provider and does not perform DNS-based SPF/DKIM/DMARC verification. Those delivery checks must be performed by the provider or a future adapter and their results passed in the signed payload. Missing or non-passing results are recorded and attachments are placed in the existing private quarantine path without OCR processing.

The upload path currently uses the repository's deterministic signature scanner. It is not a full antivirus engine; production malware scanning remains an external launch requirement. Message body size is capped at 32 MB, each and all attachments together at 25 MB, attachment count at 25, sender volume at 20 messages/hour, organization volume at 100 messages/hour, and the endpoint at 30 requests/minute per client IP.

The existing organization address endpoints support viewing and first-time creation. Safe rotation is not exposed: the checked-in schema does not define an address uniqueness constraint or an atomic organization-scoped rotate operation. A rotation implementation needs both so the previous address cannot remain active after partial failure or a concurrent request.
