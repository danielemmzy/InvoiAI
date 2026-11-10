from __future__ import annotations

import secrets
from uuid import UUID


def manage_email_address(db, *, org_id: UUID, user_id: UUID, domain: str, rotate: bool = False) -> dict:
    """Create once or rotate atomically through the database function."""
    address = f"invoices+{secrets.token_hex(24)}@{domain.strip().lower()}"
    rows = db.rpc("manage_ap_email_intake_address", {
        "p_org_id": str(org_id),
        "p_created_by": str(user_id),
        "p_email_address": address,
        "p_rotate": rotate,
    }).execute().data or []
    if isinstance(rows, dict):
        return rows
    if not rows:
        raise RuntimeError("Could not create the AP forwarding address.")
    return rows[0]
