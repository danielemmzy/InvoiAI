from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.context import OrganizationContext
from app.core.container import get_container
from app.core.ocm import get_org_context
from app.core.permissions import UPDATE_SETTINGS, VIEW_SETTINGS
from app.core.mfa import require_fresh_mfa

router = APIRouter(prefix="/organization-settings", tags=["Organization Settings"])


# The organization_settings table already contains approval_policy JSONB. We use
# that field as a namespaced policy document so the settings center can expose
# the full AP/control surface without another migration for every new policy.
DEFAULT_POLICY: dict[str, Any] = {
    "ap": {
        "enabled": True,
        "default_workflow": "auto",
        "default_match_mode": "auto",
        "allow_non_po": True,
        "require_po_above_amount": 0,
        "require_approval_all": True,
        "auto_submit": True,
        "auto_match": True,
        "auto_code": True,
        "manual_review_on_low_confidence": True,
        "invoice_intake": {
            "email_enabled": True,
            "accepted_document_types": ["invoice", "credit_note", "debit_note"],
            "auto_analyze": True,
            "auto_classify": True,
            "ocr_language": "en",
            "require_invoice_number": True,
            "require_vendor": True,
            "require_currency": True,
            "require_invoice_date": True,
            "require_due_date": False,
            "require_line_items": False,
        },
        "matching": {
            "two_way_enabled": True,
            "three_way_enabled": True,
            "quantity_tolerance_percent": 0,
            "price_tolerance_percent": 0,
            "amount_tolerance": 0,
            "tax_tolerance": 0,
            "currency_mismatch_action": "block",
            "vendor_mismatch_action": "block",
            "missing_po_action": "exception",
            "missing_receipt_action": "exception",
            "partial_receipt_action": "exception",
            "over_invoice_action": "exception",
            "under_invoice_action": "warning",
            "closed_po_action": "exception",
        },
        "exceptions": {
            "default_action": "route_to_ap",
            "auto_hold": True,
            "escalation_hours": 72,
            "max_escalation_levels": 3,
            "require_resolution_before_payment": True,
        },
    },
    "duplicate_detection": {
        "enabled": True,
        "threshold": 85,
        "window_days": 90,
        "amount_tolerance": 0,
        "action": "block_payment",
    },
    "fraud": {
        "enabled": True,
        "sensitivity": "medium",
        "auto_block_score": 95,
        "alert_email": None,
        "new_vendor_review": True,
        "unusual_amount_review": True,
        "unusual_frequency_review": True,
        "new_bank_account_review": True,
    },
    "vendor": {
        "auto_create": True,
        "match_threshold": 85,
        "require_verification": True,
        "allow_unverified_invoice": True,
        "block_inactive": True,
        "block_expired_documents": True,
        "require_tax_information": False,
        "require_bank_information": True,
        "require_approval_before_first_payment": True,
        "bank_change_independent_verification": True,
    },
    "coding": {
        "auto_coding": True,
        "confidence_threshold": 90,
        "require_coding_approval": False,
        "vendor_based_coding": True,
        "po_based_coding": True,
        "validate_gl": True,
    },
    "approvals": {
        "self_approval": False,
        "processor_can_approve": False,
        "vendor_creator_can_approve": False,
        "bank_change_requester_can_approve": False,
        "invoice_approver_can_be_sole_payment_authorizer": False,
        "payment_preparer_can_final_approve": False,
        "approval_over_authority_action": "block",
        "reminder_after_hours": 24,
        "second_reminder_after_hours": 48,
        "escalate_after_hours": 72,
        "escalate_to_supervisor": True,
        "max_escalation_levels": 3,
    },
    "payments": {
        "approval_required": True,
        "high_value_threshold": 0,
        "dual_authorization_enabled": True,
        "payment_batching_enabled": True,
        "payment_scheduling_enabled": True,
        "hold_on_exception": True,
        "hold_on_duplicate": True,
        "hold_on_unverified_vendor": True,
        "hold_on_bank_change": True,
        "early_payment_discounts_enabled": True,
        "separate_payment_approval": True,
    },
    "notifications": {
        "email_enabled": True,
        "approval_requests": True,
        "approval_overdue": True,
        "exceptions": True,
        "payment_ready": True,
        "payment_failed": True,
        "vendor_verification": True,
        "fraud_alerts": True,
        "duplicate_alerts": True,
        "integration_failures": True,
        "approval_reminder_hours": 24,
        "escalation_hours": 72,
    },
    "accounting": {
        "auto_coding": True,
        "coding_confidence_threshold": 90,
        "require_coding_approval": False,
        "default_expense_account": None,
        "default_tax_account": None,
        "default_ap_liability_account": None,
        "department_mapping": True,
        "cost_center_mapping": True,
        "tax_enabled": True,
        "tax_inclusive_invoices": False,
        "withholding_tax_enabled": False,
        "tax_mismatch_tolerance": 0,
    },
    "ai": {
        "enabled": True,
        "auto_analysis": True,
        "document_intelligence": True,
        "embeddings_enabled": True,
        "copilot_enabled": True,
        "high_confidence_threshold": 90,
        "medium_confidence_threshold": 75,
        "critical_fields_require_confidence": True,
        "critical_fields": ["vendor", "invoice_number", "currency", "total_amount", "tax", "po"],
    },
    "security": {
        "mfa_required": False,
        "session_timeout_minutes": 480,
        "sensitive_action_reauth": True,
        "payment_release_reauth": True,
        "bank_change_reauth": True,
        "role_change_reauth": True,
        "approval_authority_change_reauth": True,
        "integration_change_reauth": True,
        "ip_restrictions_enabled": False,
    },
    "audit": {
        "enabled": True,
        "log_settings_changes": True,
        "log_role_changes": True,
        "log_approval_changes": True,
        "log_vendor_changes": True,
        "log_payment_changes": True,
        "log_bank_changes": True,
        "log_integration_changes": True,
    },
    "retention": {
        "document_retention_months": 84,
        "ocr_retention_months": 84,
        "ai_data_retention_months": 24,
        "audit_log_retention_months": 84,
        "deleted_document_retention_days": 30,
    },
    "integrations": {
        "invoice_sync": True,
        "vendor_sync": True,
        "chart_of_accounts_sync": True,
        "payment_status_sync": True,
        "po_sync": True,
        "receipt_sync": True,
        "sync_frequency": "automatic",
        "max_retries": 3,
        "retry_delay_seconds": 60,
        "export_only_after_approval": True,
    },
    "branding": {
        "email_branding": True,
        "vendor_portal_branding": True,
        "email_sender_name": None,
        "email_sender_address": None,
    },
    "webhooks": {
        "enabled": False,
        "events": [],
    },
}


from app.core.db import execute

class OrganizationProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    industry: str | None = None
    company_size: str | None = None
    country: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    website: str | None = None
    logo_url: str | None = None
    tax_id: str | None = None


class SettingsUpdateRequest(BaseModel):
    organization: OrganizationProfileUpdate | None = None
    settings: dict[str, Any] | None = None
    policy_settings: dict[str, Any] | None = None


def _require(ctx: OrganizationContext, permission: str) -> None:
    if permission not in ctx.permissions and "*" not in ctx.permissions:
        raise HTTPException(status_code=403, detail="Not authorized")


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _effective_policy(raw: dict[str, Any] | None) -> dict[str, Any]:
    return _deep_merge(DEFAULT_POLICY, raw or {})


def _settings_payload(settings: Any) -> dict[str, Any]:
    data = settings.model_dump(mode="json")
    data["policy_settings"] = _effective_policy(settings.approval_policy)
    return data


@router.get("", dependencies=[Depends(require_fresh_mfa)])
async def get_organization_settings(ctx: OrganizationContext = Depends(get_org_context)):
    _require(ctx, VIEW_SETTINGS)
    service = get_container().organization_service
    organization = await service.organizations.get_organization(ctx.org_id)
    settings = await service.settings.get_settings(ctx.org_id)
    if organization is None or settings is None:
        raise HTTPException(status_code=404, detail="Organization settings not found")
    return {
        "organization": organization.model_dump(mode="json"),
        "settings": _settings_payload(settings),
        "permissions": sorted(ctx.permissions),
    }


@router.patch("", dependencies=[Depends(require_fresh_mfa)])
async def update_organization_settings(
    payload: SettingsUpdateRequest,
    ctx: OrganizationContext = Depends(get_org_context),
):
    _require(ctx, UPDATE_SETTINGS)
    service = get_container().organization_service

    if payload.organization is not None:
        org_data = payload.organization.model_dump(exclude_none=True)
        if "currency" in org_data:
            org_data["currency"] = str(org_data["currency"]).upper()
        updated_org = await service.organizations.update_organization(ctx.org_id, org_data)
        if updated_org is None:
            raise HTTPException(status_code=404, detail="Organization not found")

    current = await service.settings.get_settings(ctx.org_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Organization settings not found")

    if payload.settings is not None:
        allowed = {
            "default_currency", "supported_currencies", "timezone", "fiscal_year_start_month",
            "date_format", "number_format", "default_language", "auto_analyze", "ocr_language",
            "default_industry", "supported_document_types", "duplicate_threshold", "duplicate_window_days",
            "duplicate_amount_tolerance", "fraud_sensitivity", "auto_reject_fraud_score", "fraud_alert_email",
            "auto_create_vendors", "vendor_match_threshold", "require_vendor_verification", "ai_enabled",
            "ai_model_preference", "ai_temperature", "enable_embeddings", "copilot_enabled",
            "copilot_memory_days", "copilot_max_context_docs", "analytics_enabled", "analytics_retention_months",
            "email_notifications", "notification_email", "slack_webhook_url", "outbound_webhook_url",
            "brand_color", "custom_domain", "sso_provider", "sso_config",
        }
        data = {k: v for k, v in payload.settings.items() if k in allowed}
        if "default_currency" in data:
            data["default_currency"] = str(data["default_currency"]).upper()
        if "supported_currencies" in data:
            data["supported_currencies"] = [str(v).upper() for v in data["supported_currencies"]]
        if data:
            current = await service.settings.update_settings(ctx.org_id, data)
            if current is None:
                raise HTTPException(status_code=404, detail="Organization settings not found")

    if payload.policy_settings is not None:
        merged = _deep_merge(_effective_policy(current.approval_policy), payload.policy_settings)
        current = await service.settings.update_settings(ctx.org_id, {"approval_policy": merged})
        if current is None:
            raise HTTPException(status_code=404, detail="Organization settings not found")

    try:
        await (await execute(service.organizations.db.table("organization_settings").select("id").eq("org_id", str(ctx.org_id)).limit(1)))
        await get_container().audit_service.log(
            org_id=ctx.org_id,
            user_id=UUID(ctx.user_id),
            action="organization.settings_updated",
            resource_type="organization_settings",
            resource_id=ctx.org_id,
            old_values={},
            new_values={
                "organization": payload.organization.model_dump(exclude_none=True) if payload.organization else {},
                "settings": payload.settings or {},
                "policy_sections": sorted((payload.policy_settings or {}).keys()),
            },
        )
    except Exception:
        pass

    organization = await service.organizations.get_organization(ctx.org_id)
    settings = await service.settings.get_settings(ctx.org_id)
    return {
        "organization": organization.model_dump(mode="json"),
        "settings": _settings_payload(settings),
        "permissions": sorted(ctx.permissions),
    }
