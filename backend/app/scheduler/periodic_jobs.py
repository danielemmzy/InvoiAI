from __future__ import annotations

from app.core.container import get_container
from app.workers.ap_matching_worker import APMatchingWorker
from app.workers.ap_coding_worker import APCodingWorker
from app.workers.bill_sync_worker import BillSyncWorker
from app.workers.chart_of_accounts_sync_worker import ChartOfAccountsSyncWorker
from app.scheduler.cron import CronScheduler


cron = CronScheduler()


async def _ocr():
    return await get_container().ocr_worker.run_pending()


async def _vendor():
    return await get_container().vendor_worker.run_pending()


async def _analysis():
    return await get_container().analysis_worker.run_pending()


async def _embedding():
    return await get_container().embedding_worker.run_pending()


async def _memory():
    return await get_container().memory_worker.run_pending()


async def _quickbooks():
    return await get_container().quickbooks_worker.run_pending()


async def _xero():
    return await get_container().xero_worker.run_pending()


async def _notifications():
    return await get_container().notification_worker.run()


async def _reminders():
    return await get_container().reminder_worker.run_pending()


async def _escalations():
    return await get_container().escalation_worker.run_pending()


async def _insights():
    return await get_container().insight_worker.run_pending()


async def _token_refresh():
    return await get_container().token_refresh_worker.run()


async def _finance():
    return await get_container().finance_worker.run_pending()


async def _ap_matching():
    return await APMatchingWorker().run_pending()


async def _ap_coding():
    return await APCodingWorker().run_pending()


async def _bill_sync():
    return await BillSyncWorker().run_pending()


async def _coa_sync():
    return await ChartOfAccountsSyncWorker().run()


cron.register(name="ocr-processing", expression="*/2 * * * *", worker=_ocr)
cron.register(name="vendor-matching", expression="*/5 * * * *", worker=_vendor)
cron.register(name="analysis", expression="*/10 * * * *", worker=_analysis)
cron.register(name="embedding", expression="*/15 * * * *", worker=_embedding)
cron.register(name="memory", expression="*/30 * * * *", worker=_memory)
cron.register(name="quickbooks-sync", expression="0 * * * *", worker=_quickbooks)
cron.register(name="xero-sync", expression="10 * * * *", worker=_xero)
cron.register(name="notification-delivery", expression="* * * * *", worker=_notifications)
cron.register(name="approval-reminders", expression="*/15 * * * *", worker=_reminders)
cron.register(name="approval-escalation", expression="*/15 * * * *", worker=_escalations)
cron.register(name="insights", expression="0 */6 * * *", worker=_insights)
cron.register(name="token-refresh", expression="0 * * * *", worker=_token_refresh)
cron.register(name="finance-maintenance", expression="5 0 * * *", worker=_finance)
cron.register(name="ap-matching", expression="*/2 * * * *", worker=_ap_matching)
cron.register(name="ap-coding", expression="*/2 * * * *", worker=_ap_coding)
cron.register(name="ap-bill-sync", expression="*/5 * * * *", worker=_bill_sync)
cron.register(name="quickbooks-coa-sync", expression="17 */6 * * *", worker=_coa_sync)
