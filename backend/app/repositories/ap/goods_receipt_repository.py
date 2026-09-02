from uuid import UUID
from app.repositories.base import BaseRepository
from app.mappers.ap.goods_receipt_mapper import GoodsReceiptMapper
class GoodsReceiptRepository(BaseRepository):
    table_name="goods_receipts"; mapper=GoodsReceiptMapper
    async def list_by_po(self, org_id: UUID, purchase_order_id: UUID):
        return self._many(self.table().select("*, goods_receipt_lines(*)").eq("org_id",str(org_id)).eq("purchase_order_id",str(purchase_order_id)).execute())
    async def get_confirmed_for_po(self, org_id: UUID, purchase_order_id: UUID):
        return self._many(self.table().select("*, goods_receipt_lines(*)").eq("org_id",str(org_id)).eq("purchase_order_id",str(purchase_order_id)).in_("status",["confirmed","complete"]).execute())
