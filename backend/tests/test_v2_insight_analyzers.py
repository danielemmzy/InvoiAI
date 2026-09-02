import pytest
from types import SimpleNamespace
from uuid import uuid4

from app2.services.insights.analyzers.receivable_analyzer import ReceivableAnalyzer
from app2.services.insights.analyzers.spending_analyzer import SpendingAnalyzer
from app2.services.insights.analyzers.vendor_analyzer import VendorAnalyzer
from app2.services.insights.analyzers.subscription_analyzer import SubscriptionAnalyzer
from app2.services.insights.analyzers.cashflow_analyzer import CashflowAnalyzer
from app2.services.insights.analyzers.payable_analyzer import PayableAnalyzer


class EmptyDocuments:
    async def list_by_status(self, *args, **kwargs):
        return []
    async def list_overdue(self, *args, **kwargs):
        return []
    async def list_vendor_documents(self, *args, **kwargs):
        return []
    async def list_documents_by_date_range(self, *args, **kwargs):
        return []
    async def list_documents_for_spending(self, *args, **kwargs):
        return []
    async def list_line_items_for_documents(self, *args, **kwargs):
        return []


class EmptyVendors:
    async def top_vendors_by_spend(self, *args, **kwargs):
        return []
    async def top_vendors_by_documents(self, *args, **kwargs):
        return []


class EmptyPayments:
    async def list_org_payments(self, *args, **kwargs):
        return []


@pytest.mark.asyncio
async def test_all_six_insight_analyzers_handle_empty_organization_safely():
    org_id = uuid4()

    receivable = await ReceivableAnalyzer(EmptyDocuments()).run(org_id)
    spending = await SpendingAnalyzer(EmptyDocuments()).run(org_id)
    vendor = await VendorAnalyzer(EmptyVendors(), EmptyDocuments()).run(org_id)
    subscription = await SubscriptionAnalyzer(EmptyVendors(), EmptyDocuments()).run(org_id)
    cashflow = await CashflowAnalyzer(EmptyDocuments(), EmptyPayments()).run(org_id)
    payable = await PayableAnalyzer(EmptyDocuments()).run(org_id)

    assert receivable.name == "receivable"
    assert spending.name == "spending"
    assert vendor.name == "vendor"
    assert subscription.name == "subscription"
    assert cashflow.name == "cashflow"
    assert payable.name == "payable"
    assert all(isinstance(result.data, dict) for result in [
        receivable, spending, vendor, subscription, cashflow, payable
    ])
