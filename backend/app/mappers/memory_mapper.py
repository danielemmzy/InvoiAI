"""
============================================================
Memory Mapper

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

from app.models.domain.memory import (
    DocumentMemory,
    OrganizationMemory,
    VendorMemory,
)

from app.schemas.memory import (
    DocumentMemoryResponse,
    OrganizationMemoryResponse,
    VendorMemoryResponse,
)


class DocumentMemoryMapper(
    BaseMapper[
        DocumentMemory,
        DocumentMemoryResponse,
    ]
):
    domain_model = DocumentMemory
    response_model = DocumentMemoryResponse


class VendorMemoryMapper(
    BaseMapper[
        VendorMemory,
        VendorMemoryResponse,
    ]
):
    domain_model = VendorMemory
    response_model = VendorMemoryResponse


class OrganizationMemoryMapper(
    BaseMapper[
        OrganizationMemory,
        OrganizationMemoryResponse,
    ]
):
    domain_model = OrganizationMemory
    response_model = OrganizationMemoryResponse