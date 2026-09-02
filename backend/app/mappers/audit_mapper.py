"""
============================================================
Audit Mapper
============================================================
"""

from app.mappers.base import BaseMapper

from app.models.domain.audit import AuditLog

from app.schemas.audit import AuditLogResponse


class AuditLogMapper(
    BaseMapper[
        AuditLog,
        AuditLogResponse,
    ]
):
    domain_model = AuditLog
    response_model = AuditLogResponse