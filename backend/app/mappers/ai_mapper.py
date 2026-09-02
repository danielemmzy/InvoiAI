"""
============================================================
AI Mapper

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

from app.models.domain.ai import (
    AIEvent,
    AIScoreExplanation,
)

from app.schemas.ai import (
    AIEventResponse,
    AIScoreExplanationResponse,
)


class AIEventMapper(
    BaseMapper[
        AIEvent,
        AIEventResponse,
    ]
):
    domain_model = AIEvent
    response_model = AIEventResponse


class AIScoreExplanationMapper(
    BaseMapper[
        AIScoreExplanation,
        AIScoreExplanationResponse,
    ]
):
    domain_model = AIScoreExplanation
    response_model = AIScoreExplanationResponse