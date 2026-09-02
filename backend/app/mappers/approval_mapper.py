"""
============================================================
Approval Mapper
============================================================
"""

from app.mappers.base import BaseMapper

from app.models.domain.approval import (
    ApprovalHistory,
    ApprovalStep,
    ApprovalWorkflow,
)

from app.schemas.approval import (
    ApprovalHistoryResponse,
    ApprovalStepResponse,
    ApprovalWorkflowResponse,
)


class ApprovalWorkflowMapper(
    BaseMapper[
        ApprovalWorkflow,
        ApprovalWorkflowResponse,
    ]
):
    domain_model = ApprovalWorkflow
    response_model = ApprovalWorkflowResponse


class ApprovalStepMapper(
    BaseMapper[
        ApprovalStep,
        ApprovalStepResponse,
    ]
):
    domain_model = ApprovalStep
    response_model = ApprovalStepResponse


class ApprovalHistoryMapper(
    BaseMapper[
        ApprovalHistory,
        ApprovalHistoryResponse,
    ]
):
    domain_model = ApprovalHistory
    response_model = ApprovalHistoryResponse