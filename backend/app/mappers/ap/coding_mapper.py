from app.mappers.base import BaseMapper
from app.models.domain.ap import InvoiceCoding, CodingRule
class InvoiceCodingMapper(BaseMapper):
    domain_model = InvoiceCoding
    response_model = InvoiceCoding
    @staticmethod
    def to_insert(data):
        payload = data.model_dump(mode="json", exclude_none=True) if hasattr(data, "model_dump") else dict(data)
        payload.pop("id", None); payload.pop("created_at", None); payload.pop("updated_at", None)
        return payload
class CodingRuleMapper(BaseMapper):
    domain_model = CodingRule
    response_model = CodingRule
    @staticmethod
    def to_insert(data):
        payload = data.model_dump(mode="json", exclude_none=True) if hasattr(data, "model_dump") else dict(data)
        payload.pop("id", None); payload.pop("created_at", None); payload.pop("updated_at", None)
        return payload
