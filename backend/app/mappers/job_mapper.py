"""
============================================================
Job Mapper
============================================================
"""

from app.mappers.base import BaseMapper

from app.models.domain.job import BackgroundJob

from app.schemas.job import JobResponse


class BackgroundJobMapper(
    BaseMapper[
        BackgroundJob,
        JobResponse,
    ]
):
    domain_model = BackgroundJob
    response_model = JobResponse