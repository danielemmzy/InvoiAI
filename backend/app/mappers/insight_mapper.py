"""
============================================================
Insight Mapper
============================================================
"""

from app.mappers.base import BaseMapper
from app.models.domain.insight import Insight
from app.schemas.insight import InsightResponse


class InsightMapper(BaseMapper[Insight, InsightResponse]):
    domain_model = Insight
    response_model = InsightResponse
