"""
============================================================
Organization Mapper
============================================================
"""

from app.core.enum.database import PlanType
from app.core.plan import document_limit_for
from app.mappers.base import BaseMapper

from app.models.domain.organization import (
    Organization,
    OrganizationMember,
    OrganizationSettings,
    OrganizationUsage,
)

from app.schemas.organization import (
    OrganizationMemberResponse,
    OrganizationResponse,
    OrganizationSettingsResponse,
    OrganizationUsageResponse,
)


class OrganizationMapper(
    BaseMapper[
        Organization,
        OrganizationResponse,
    ]
):
    domain_model = Organization
    response_model = OrganizationResponse

    @classmethod
    def to_domain(
        cls,
        row: dict | None,
    ) -> Organization | None:
        if row is None:
            return None

        payload = dict(row)

        if payload.get("document_limit") is None:
            plan = payload.get("plan")

            if isinstance(plan, PlanType):
                plan_type = plan
            else:
                try:
                    plan_type = PlanType(str(plan or "free").lower())
                except ValueError:
                    plan_type = PlanType.FREE

            payload["document_limit"] = document_limit_for(plan_type)

        return cls.domain_model.model_validate(payload)


class OrganizationSettingsMapper(
    BaseMapper[
        OrganizationSettings,
        OrganizationSettingsResponse,
    ]
):
    domain_model = OrganizationSettings
    response_model = OrganizationSettingsResponse


class OrganizationMemberMapper(
    BaseMapper[
        OrganizationMember,
        OrganizationMemberResponse,
    ]
):
    domain_model = OrganizationMember
    response_model = OrganizationMemberResponse


class OrganizationUsageMapper(
    BaseMapper[
        OrganizationUsage,
        OrganizationUsageResponse,
    ]
):
    domain_model = OrganizationUsage
    response_model = OrganizationUsageResponse