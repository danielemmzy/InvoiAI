from app.mappers.base import BaseMapper
from app.models.domain.ap import (
    ApprovalGroup,
    ApprovalGroupMember,
    ApprovalRule,
    PaymentAuthorization,
    InvoiceComment,
    PaymentInstruction,
    PaymentInstructionEvent,
    VendorDocumentRequest,
)


class ApprovalGroupMapper(BaseMapper):
    domain_model = ApprovalGroup
    response_model = ApprovalGroup


class ApprovalGroupMemberMapper(BaseMapper):
    domain_model = ApprovalGroupMember
    response_model = ApprovalGroupMember


class ApprovalRuleMapper(BaseMapper):
    domain_model = ApprovalRule
    response_model = ApprovalRule


class PaymentAuthorizationMapper(BaseMapper):
    domain_model = PaymentAuthorization
    response_model = PaymentAuthorization


class InvoiceCommentMapper(BaseMapper):
    domain_model = InvoiceComment
    response_model = InvoiceComment


class PaymentInstructionMapper(BaseMapper):
    domain_model = PaymentInstruction
    response_model = PaymentInstruction


class PaymentInstructionEventMapper(BaseMapper):
    domain_model = PaymentInstructionEvent
    response_model = PaymentInstructionEvent


class VendorDocumentRequestMapper(BaseMapper):
    domain_model = VendorDocumentRequest
    response_model = VendorDocumentRequest