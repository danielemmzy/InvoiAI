from app.mappers.base import BaseMapper
from app.models.domain.ap import InvoiceException
class InvoiceExceptionMapper(BaseMapper):
    domain_model = InvoiceException
    response_model = InvoiceException
