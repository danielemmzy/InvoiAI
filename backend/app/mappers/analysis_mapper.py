"""
============================================================
Analysis Mapper

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

from app.models.domain.analysis import Analysis

from app.schemas.analysis import AnalysisResponse


class AnalysisMapper(
    BaseMapper[
        Analysis,
        AnalysisResponse,
    ]
):
    """
    Mapper for document analyses.
    """

    domain_model = Analysis
    response_model = AnalysisResponse