import json
import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.workspace import CompanySize, WorkspaceSummary

BusinessType = Literal["registered_company", "sole_trader", "partnership", "not_registered"]
AccountingSoftware = Literal["xero", "quickbooks", "sage", "none", "not_sure"]
InvoiceVolume = Literal["1-10", "11-25", "26-100", "101-500", "500+"]
Industry = Literal["consulting", "professional_services", "agency", "technology", "construction", "healthcare", "other"]


class OnboardingDraftUpdate(BaseModel):
    step: int = Field(ge=1, le=6)
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("data")
    @classmethod
    def bound_draft_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value, ensure_ascii=False)) > 16_384:
            raise ValueError("Onboarding draft is too large")
        return value


class OnboardingDraftResponse(BaseModel):
    step: int = 1
    completed: bool = False
    data: dict[str, Any] = Field(default_factory=dict)
    workspace_id: UUID | None = None


class OnboardingComplete(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    country: str = Field(min_length=2, max_length=2)
    currency: str = Field(min_length=3, max_length=3)
    business_type: BusinessType
    industry: Industry
    company_size: CompanySize
    monthly_invoice_volume: InvoiceVolume
    accounting_software: AccountingSoftware
    invite_emails: list[str] = Field(default_factory=list, max_length=10)
    approver_email: str | None = None

    @field_validator("invite_emails")
    @classmethod
    def validate_invite_emails(cls, value: list[str]) -> list[str]:
        email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        normalized = [email.strip().lower() for email in value]
        if any(len(email) > 254 or not email_pattern.match(email) for email in normalized):
            raise ValueError("Enter valid teammate email addresses")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Teammate email addresses must be unique")
        return normalized

    @field_validator("approver_email")
    @classmethod
    def validate_approver_email(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().lower()
        if len(normalized) > 254 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
            raise ValueError("Enter a valid approver email address")
        return normalized


class OnboardingCompleteResponse(BaseModel):
    workspace: WorkspaceSummary
    completed: bool = True
