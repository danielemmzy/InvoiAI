"""
============================================================
Vendor Mapper
============================================================
"""

from app.mappers.base import BaseMapper

from app.models.domain.vendor import Vendor

from app.schemas.vendor import VendorResponse


class VendorMapper(
    BaseMapper[
        Vendor,
        VendorResponse,
    ]
):
    domain_model = Vendor
    response_model = VendorResponse