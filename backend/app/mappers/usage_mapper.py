"""
============================================================
Usage Mapper

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

from app.models.domain.usage import Usage

from app.schemas.usage import UsageResponse


class UsageMapper(
    BaseMapper[
        Usage,
        UsageResponse,
    ]
):
    domain_model = Usage
    response_model = UsageResponse