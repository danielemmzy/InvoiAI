from app.mappers.base import BaseMapper
from app.models.domain.ap import ChartOfAccount
class ChartOfAccountMapper(BaseMapper):
    domain_model = ChartOfAccount
    response_model = ChartOfAccount
