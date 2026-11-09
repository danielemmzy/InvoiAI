# Storage security gates

Local intake validates document content, hashes the received bytes, writes to the private `documents` bucket, and routes deterministic scanner findings to `quarantine/`. Quarantined documents are persisted for operator review with failed pipeline state, so the OCR queue does not process them. Signed downloads are limited to five minutes, and upload paths cannot overwrite an existing object.

The in-process `SignatureScanner` is a deterministic policy/test scanner, not a production anti-malware engine. Configure and verify a maintained malware scanning service before accepting production uploads; fail closed if scanning is unavailable. No malware vendor or production scanning coverage is asserted here.

The migration marks an existing Supabase `documents` bucket private and restricts its size/MIME types. Confirm bucket provisioning, private status, and deployed storage policies in the target Supabase project before production; a local migration cannot verify project state.

No backup destination or restore target is configured in this repository. A real backup restore and record verification remain a release gate; do not report backup/restore as tested until the target is configured and a restore is performed. Retention periods remain subject to legal review. The current user-facing delete action archives records; it does not physically delete documents or approval history. Any future purge process must preserve open approvals and audit records and be verified against the approved retention policy.
