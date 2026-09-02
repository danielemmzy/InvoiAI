"""
============================================================
Organization Service

Business logic for organizations.

Responsibilities
----------------
- Organization lifecycle
- Organization Context (OCM)
- Active organization selection
- Organization feature resolution
- Organization settings lookup

No SQL.

Repositories own persistence.

============================================================
"""

from __future__ import annotations

from uuid import UUID, uuid4
import re
from datetime import UTC, datetime

from fastapi import HTTPException, status
import logging

from app.context.organization import OrganizationContext
from app.context.auth import AuthUser

from app.models.domain.organization import Organization

from app.repositories.organization.organization_repository import (
    OrganizationRepository,
)
from app.repositories.organization.organization_settings_repository import (
    OrganizationSettingsRepository,
)
from app.repositories.organization.member_repository import (
    MemberRepository,
)
from app.repositories.organization.usage_repository import (
    UsageRepository,
)

from app.core.permissions import get_permissions
from app.schemas.workspace import WorkspaceSummary
from app.core.enum.database import OrgRole, PlanType
from app.core.plan import document_limit_for


logger = logging.getLogger(__name__)

class OrganizationService:
    """
    Business logic for organizations.

    This service is responsible for constructing the
    OrganizationContext used throughout the application.
    """

    def __init__(self):

        self.organizations = OrganizationRepository()

        self.settings = OrganizationSettingsRepository()

        self.members = MemberRepository()

        self.usage = UsageRepository()

    # ======================================================
    # Internal helpers
    # ======================================================

    async def _get_organization(
        self,
        org_id: UUID,
    ) -> Organization:

        organization = await self.organizations.get_organization(
            org_id,
        )

        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        return organization

    async def _get_member(
        self,
        *,
        org_id: UUID,
        user_id: UUID,
    ):

        member = await self.members.get_org_member(
            org_id,
            user_id,
        )

        if member is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization.",
            )

        if not member.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Membership is inactive.",
            )

        return member

    async def _get_settings(
        self,
        org_id: UUID,
    ):

        settings = await self.settings.get_settings(
            org_id,
        )

        if settings is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Organization settings are missing.",
            )

        return settings

    async def _get_usage(
        self,
        org_id: UUID,
    ):

        month = self.usage.current_month()

        usage = await self.usage.get_current_usage(
            org_id,
            month,
        )

        return usage
    
        # ======================================================
    # Organization Context (OCM)
    # ======================================================

    async def build_context(
        self,
        *,
        user: AuthUser,
        org_id: str | None = None,
    ) -> OrganizationContext:
        """
        Build the OrganizationContext for the current request.

        This is the primary entrypoint used by the OCM dependency.
        """

        # --------------------------------------------------
        # Determine active organization
        # --------------------------------------------------

        if org_id is None:

            memberships = await self.members.list_user_memberships(
                user.id,
            )

            if not memberships:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not belong to any organization.",
                )

            membership = memberships[0]

            org_uuid = membership.org_id

        else:

            org_uuid = UUID(org_id)

            membership = await self._get_member(
                org_id=org_uuid,
                user_id=user.id,
            )

        # --------------------------------------------------
        # Load organization resources
        # --------------------------------------------------

        organization = await self._get_organization(
            org_uuid,
        )

        settings = await self._get_settings(
            org_uuid,
        )

        usage = await self._get_usage(
            org_uuid,
        )

        # --------------------------------------------------
        # Usage
        # --------------------------------------------------

        documents_used = 0
        storage_bytes = 0
        ai_tokens = 0
        ai_cost = 0

        if usage:

            documents_used = usage.documents_processed

            storage_bytes = usage.storage_used_bytes

            ai_tokens = usage.ai_tokens_used

            ai_cost = usage.ai_cost_usd

        remaining = max(
            organization.document_limit - documents_used,
            0,
        )

        # --------------------------------------------------
        # Features
        # --------------------------------------------------

        features = organization.features or {}

        # --------------------------------------------------
        # Build Context
        # --------------------------------------------------

        return OrganizationContext(

            org_id=organization.id,

            name=organization.name,

            slug=organization.slug,

            plan=organization.plan,

            role=membership.role,
            permissions=get_permissions(membership.role),

            document_limit=organization.document_limit,

            documents_used=documents_used,

            remaining_documents=remaining,

            ai_enabled=features.get(
                "ai_enabled",
                True,
            ),

            copilot_enabled=features.get(
                "copilot_enabled",
                True,
            ),

            analytics_enabled=features.get(
                "analytics_enabled",
                True,
            ),

            embeddings_enabled=features.get(
                "embeddings_enabled",
                True,
            ),

            default_currency=settings.default_currency,

            timezone=settings.timezone,

            feature_flags=features,

            metadata={
                "role": membership.role,
            },

            storage_bytes=storage_bytes,

            ai_tokens_used=ai_tokens,

            ai_cost_usd=ai_cost,
        )


    # ======================================================
    # Workspace lifecycle
    # ======================================================

    @staticmethod
    def _slugify(value: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return value or "workspace"

    async def list_user_workspaces(self, user_id: UUID) -> list[WorkspaceSummary]:
        memberships = await self.members.list_user_memberships(user_id)
        if not memberships:
            return []
        result: list[WorkspaceSummary] = []
        for membership in memberships:
            if not membership.is_active:
                continue
            org = await self.organizations.get_organization(membership.org_id)
            if org is None:
                continue
            workspace_type = "personal" if bool((org.features or {}).get("personal_mode")) else "business"
            result.append(WorkspaceSummary(
                id=org.id, name=org.name, slug=org.slug, type=workspace_type,
                role=membership.role, plan=org.plan, currency=org.currency,
                created_at=org.created_at,
            ))
        return result

    async def create_workspace(
        self,
        *,
        user: AuthUser,
        workspace_type: str,
        name: str | None,
        currency: str,
        country: str | None,
        company_size: str | None = None,
    ) -> WorkspaceSummary:
        workspace_type = workspace_type.lower()

        if workspace_type not in {"personal", "business"}:
            raise HTTPException(
                status_code=400,
                detail="Workspace type must be personal or business.",
            )

        # --------------------------------------------------
        # Personal workspace
        # --------------------------------------------------

        if workspace_type == "personal":
            existing = [
                workspace
                for workspace in await self.list_user_workspaces(user.id)
                if workspace.type == "personal"
            ]

            if existing:
                return existing[0]

            display_name = "Personal"

        # --------------------------------------------------
        # Business workspace
        # --------------------------------------------------

        else:
            display_name = (name or "My Business").strip()

            if len(display_name) < 2:
                raise HTTPException(
                    status_code=400,
                    detail="Business name must be at least 2 characters.",
                )

        # --------------------------------------------------
        # Organization
        # --------------------------------------------------

        org_id = uuid4()

        slug = (
            f"{self._slugify(display_name)}-"
            f"{str(org_id)[:8]}"
        )

        features = {
            "personal_mode": workspace_type == "personal",
            "ai_enabled": True,
            "copilot_enabled": True,
            "analytics_enabled": True,
            "embeddings_enabled": True,
        }

        organization = await self.organizations.create_organization(
            {
                "id": org_id,
                "name": display_name,
                "slug": slug,
                "plan": PlanType.FREE.value,
                "industry": (
                    None
                    if workspace_type == "personal"
                    else "general"
                ),
                "company_size": (
                    company_size
                    if workspace_type == "business"
                    else None
                ),
                "country": country,
                "currency": currency,
                "tax_id": None,
                "logo_url": None,
                "website": None,
                "stripe_customer_id": None,
                "document_limit": document_limit_for(
                    PlanType.FREE
                ),
                "features": features,
                "created_by": user.id,
            }
        )

        if organization is None:
            raise HTTPException(
                status_code=500,
                detail="Unable to create workspace.",
            )

        # --------------------------------------------------
        # Bootstrap workspace resources
        # --------------------------------------------------

        try:
            await self.members.create_membership(
                {
                    "org_id": org_id,
                    "user_id": user.id,
                    "role": OrgRole.OWNER.value,
                    "is_active": True,
                    "joined_at": datetime.now(UTC),
                }
            )

            month = self.usage.current_month()

            # --------------------------------------------------
            # Organization settings
            # --------------------------------------------------

            if not await self.settings.settings_exist(org_id):
                await self.settings.create_settings(
                    {
                        "org_id": org_id,
                        "default_currency": currency,
                        "supported_currencies": [currency],
                        "timezone": "UTC",
                        "fiscal_year_start_month": 1,
                        "date_format": "YYYY-MM-DD",
                        "number_format": "1,234.56",
                        "default_language": "en",
                        "auto_analyze": True,
                        "ocr_language": "en",
                        "default_industry": "general",
                        "supported_document_types": [
                            "invoice",
                            "receipt",
                        ],
                        "approval_policy": {},
                        "duplicate_threshold": 85,
                        "duplicate_window_days": 90,
                        "duplicate_amount_tolerance": 0,
                        "fraud_sensitivity": "medium",
                        "auto_reject_fraud_score": 95,
                        "fraud_alert_email": None,
                        "auto_create_vendors": True,
                        "vendor_match_threshold": 85,
                        "require_vendor_verification": False,
                        "ai_enabled": True,
                        "ai_model_preference": "gpt-4o-mini",
                        "ai_temperature": 0,
                        "enable_embeddings": True,
                        "copilot_enabled": True,
                        "copilot_memory_days": 30,
                        "copilot_max_context_docs": 20,
                        "analytics_enabled": True,
                        "analytics_retention_months": 24,
                        "email_notifications": True,
                        "notification_email": None,
                        "slack_webhook_url": None,
                        "outbound_webhook_url": None,
                        "brand_color": None,
                        "custom_domain": None,
                        "sso_provider": None,
                        "sso_config": {},
                    }
                )

            # --------------------------------------------------
            # Organization usage
            # --------------------------------------------------

            if not await self.usage.usage_exists(
                org_id,
                month,
            ):
                await self.usage.create_usage(
                    {
                        "org_id": org_id,
                        "month": month,
                        "documents_processed": 0,
                        "storage_used_bytes": 0,
                        "ai_tokens_used": 0,
                        "api_calls": 0,
                        "ai_cost_usd": 0,
                        "created_by": user.id,
                    }
                )

        except Exception:
            # Compensation keeps the multi-step bootstrap from
            # leaving an orphaned workspace.
            try:
                memberships = (
                    await self.members.list_organization_members(
                        org_id
                    )
                )

                for membership in memberships:
                    await self.members.delete_membership(
                        membership.id
                    )

            finally:
                await self.organizations.delete_organization(
                    org_id
                )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Workspace setup could not be completed. "
                    "Please try again."
                ),
            )

        # --------------------------------------------------
        # Final response
        # --------------------------------------------------

        return WorkspaceSummary(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            type=workspace_type,
            role=OrgRole.OWNER.value,
            plan=organization.plan,
            currency=organization.currency,
            created_at=organization.created_at,
        )
    # ======================================================
    # Permission Helpers
    # ======================================================

    async def get_permissions(
        self,
        *,
        org_id: UUID,
        user_id: UUID,
    ) -> set[str]:

        member = await self._get_member(
            org_id=org_id,
            user_id=user_id,
        )

        return get_permissions(
            member.role,
        )

    async def has_permission(
        self,
        *,
        org_id: UUID,
        user_id: UUID,
        permission: str,
    ) -> bool:

        permissions = await self.get_permissions(
            org_id=org_id,
            user_id=user_id,
        )

        return permission in permissions