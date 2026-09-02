"""
============================================================
Profile Mapper

Converts between:

Database
↓
Domain

Domain
↓
Response
============================================================
"""

from app.mappers.base import BaseMapper

from app.models.domain.profile import (
    Profile,
)

from app.schemas.profile import (
    ProfileResponse,
)


class ProfileMapper(
    BaseMapper[
        Profile,
        ProfileResponse,
    ]
):
    domain_model = Profile
    response_model = ProfileResponse