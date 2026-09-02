from app.mappers.base import BaseMapper
from app.models.domain.ap import GoodsReceipt, GoodsReceiptLine
class GoodsReceiptMapper(BaseMapper):
    domain_model = GoodsReceipt
    response_model = GoodsReceipt
    @classmethod
    def to_domain(cls, row):
        if not row: return None
        data = dict(row)
        data["lines"] = [GoodsReceiptLine.model_validate(x) for x in data.pop("goods_receipt_lines", [])]
        return GoodsReceipt.model_validate(data)
