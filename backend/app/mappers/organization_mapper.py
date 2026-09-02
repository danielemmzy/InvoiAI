"""
============================================================
Organization Mapper
============================================================
"""

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