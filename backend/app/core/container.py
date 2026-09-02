"""V2 dependency-injection composition root.

Production objects are constructed here so routers and schedulers do not
scatter repository/service construction throughout the application.
"""
from __future__ import annotations

from functools import cached_property
from typing import Any

from app.core.supabase import get_supabase
from app.integrations.google.google_document_ai_service import GoogleDocumentAIService
from app.integrations.quickbooks.sync_service import QuickBooksSyncService
from app.integrations.xero.sync_service import XeroSyncService
from app.repositories.ai.embedding_repository import EmbeddingRepository
from app.repositories.approval.history_repository import ApprovalHistoryRepository
from app.repositories.approval.step_repository import ApprovalStepRepository
from app.repositories.approval.workflow_repository import ApprovalWorkflowRepository
from app.repositories.audit.audit_repository import AuditRepository
from app.repositories.document.analysis_repository import AnalysisRepository
from app.repositories.document.document_repository import DocumentRepository
from app.repositories.document.purchase_order_repository import PurchaseOrderRepository
from app.repositories.document.vendor_repository import VendorRepository
from app.repositories.document.payment_repository import PaymentRepository
from app.repositories.integration.integration_repository import IntegrationConnectionRepository
from app.repositories.organization.member_repository import MemberRepository
from app.repositories.organization.organization_repository import OrganizationRepository
from app.repositories.organization.usage_repository import UsageRepository
from app.repositories.notification.notification_delivery_repository import NotificationDeliveryRepository
from app.repositories.notification.notification_repository import NotificationRepository
from app.services.analysis.analysis_service import AnalysisService
from app.services.approval.approval_engine import ApprovalEngine
from app.services.approval.approval_history_service import ApprovalHistoryService
from app.services.approval.approval_step_service import ApprovalStepService
from app.services.approval.approval_workflow_service import ApprovalWorkflowService
from app.services.audit_service import AuditService
from app.services.embedding_service import EmbeddingService
from app.services.organization_service import OrganizationService
from app.services.member_service import MemberService
from app.services.finance.income_service import IncomeService
from app.services.finance.expense_service import ExpenseService
from app.services.finance.planning_service import PlanningService
from app.repositories.ai.chat_repository import ChatRepository
from app.services.ai.copilot_service import CopilotService
from app.services.ai.tool_executor_service import ToolExecutor
from app.services.search_service import SearchService
from app.services.notification.notification_delivery_service import NotificationDeliveryService
from app.services.notification.notification_dispatcher import NotificationDispatcher
from app.services.notification.notification_service import NotificationService
from app.services.notification.provider.email_provider import EmailNotificationProvider
from app.services.notification.provider.in_app_provider import InAppNotificationProvider
from app.services.notification.provider.push_provider import PushNotificationProvider
from app.services.notification.provider.sms_provider import SMSNotificationProvider
from app.services.notification.queue.database_queue import DatabaseNotificationQueue
from app.services.ocr.ocr_service import OCRService
from app.services.storage.storage import StorageService
from app.services.validation_service import ValidationService
from app.services.document.document_service import DocumentService
from app.services.document.document_upload_service import DocumentUploadService
from app.services.vendor.vendor_memory_service import VendorMemoryService
from app.services.vendor.vendor_service import VendorService
from app.services.verification.compliance_check import ComplianceCheck
from app.services.verification.duplicate_check import DuplicateCheck
from app.services.verification.engine import VerificationEngine
from app.services.verification.fraud_check import FraudCheck
from app.services.verification.historical_check import HistoricalCheck
from app.services.verification.math_check import MathCheck
from app.services.verification.ocr_validation import OCRValidation
from app.services.verification.po_match import PurchaseOrderMatch
from app.services.verification.vendor_check import VendorCheck

from app.services.auth.auth_service import AuthService
from app.services.billing.stripe_service import StripeBillingService
from app.services.billing.stripe_event_processor import StripeEventProcessor
from app.repositories.billing.stripe_event_repository import StripeEventRepository
from app.services.export.exporter_service import ExportService
from app.repositories.organization.subscription_repository import SubscriptionRepository
from app.workers.analysis_worker import AnalysisWorker
from app.workers.approval_worker import ApprovalWorker
from app.workers.embedding_worker import EmbeddingWorker
from app.workers.finance_worker import FinanceWorker
from app.workers.insight_worker import InsightWorker
from app.workers.memory_worker import MemoryWorker
from app.workers.notification_worker import NotificationWorker
from app.workers.ocr_worker import OCRWorker
from app.workers.quickbooks_worker import QuickBooksWorker
from app.workers.reminder_worker import ReminderWorker
from app.workers.escalation_worker import EscalationWorker
from app.workers.audit_worker import AuditWorker
from app.workers.token_refresh_worker import TokenRefreshWorker
from app.workers.vendor_worker import VendorWorker
from app.workers.xero_worker import XeroWorker
from app.services.insights.insight_service import InsightService
from app.services.integration_service import IntegrationService
from app.services.usage_service import UsageService
from app.services.token_service import TokenService
from app.integrations.quickbooks.oauth import QuickBooksOAuth
from app.integrations.xero.oauth import XeroOAuth


class Container:
    """Singleton-style V2 composition root with lazy construction."""

    @cached_property
    def db(self):
        return get_supabase()

    @cached_property
    def document_repository(self):
        return DocumentRepository()

    @cached_property
    def document_service(self):
        return DocumentService(
            repository=self.document_repository,
        )

    @cached_property
    def document_upload_service(self):
        return DocumentUploadService(
            document_service=self.document_service,
            storage_service=self.storage_service,
        )

    @cached_property
    def analysis_repository(self):
        return AnalysisRepository()

    @cached_property
    def purchase_order_repository(self):
        return PurchaseOrderRepository()

    @cached_property
    def purchase_order_service(self):
        from app.services.purchase.purchase_order_service import PurchaseOrderService
        return PurchaseOrderService()

    @cached_property
    def embedding_repository(self):
        return EmbeddingRepository()

    @cached_property
    def vendor_repository(self):
        return VendorRepository()

    @cached_property
    def storage_service(self):
        return StorageService(client=self.db)

    @cached_property
    def google_document_ai(self):
        return GoogleDocumentAIService()

    @cached_property
    def validation_service(self):
        return ValidationService(math_check=MathCheck())

    @cached_property
    def verification_engine(self):
        return VerificationEngine(
            ocr_validation=OCRValidation(),
            math_check=MathCheck(),
            vendor_check=VendorCheck(),
            duplicate_check=DuplicateCheck(),
            historical_check=HistoricalCheck(),
            po_match=PurchaseOrderMatch(),
            fraud_check=FraudCheck(),
            compliance_check=ComplianceCheck(),
        )

    @cached_property
    def embedding_service(self):
        return EmbeddingService(repository=self.embedding_repository)

    @cached_property
    def embedding_worker(self):
        return EmbeddingWorker(
            repository=self.document_repository,
            embedding_service=self.embedding_service,
        )

    @cached_property
    def analysis_service(self):
        return AnalysisService(
            repository=self.analysis_repository,
            document_repository=self.document_repository,
            purchase_order_repository=self.purchase_order_repository,
            verification_engine=self.verification_engine,
            embedding_worker=self.embedding_worker,
            validation_service=self.validation_service,
        )

    @cached_property
    def analysis_worker(self):
        return AnalysisWorker(analysis_service=self.analysis_service, document_repository=self.document_repository)

    @cached_property
    def ocr_service(self):
        return OCRService(
            document_repository=self.document_repository,
            storage_service=self.storage_service,
            provider=self.google_document_ai,
            analysis_worker=self.analysis_worker,
        )

    @cached_property
    def ocr_worker(self):
        return OCRWorker(ocr_service=self.ocr_service, document_repository=self.document_repository)

    @cached_property
    def vendor_memory_service(self):
        return VendorMemoryService(repository=self.vendor_repository)

    @cached_property
    def vendor_worker(self):
        return VendorWorker(vendor_memory_service=self.vendor_memory_service, vendor_repository=self.vendor_repository)

    @cached_property
    def memory_worker(self):
        return MemoryWorker(
            vendor_repository=self.vendor_repository,
            memory_service=self.vendor_memory_service,
        )

    @cached_property
    def notification_repository(self):
        return NotificationRepository()

    @cached_property
    def notification_delivery_repository(self):
        return NotificationDeliveryRepository()

    @cached_property
    def notification_queue(self):
        return DatabaseNotificationQueue(self.db)

    @cached_property
    def notification_dispatcher(self):
        from app.core.enum.notification import NotificationChannel
        return NotificationDispatcher(
            queue=self.notification_queue,
            providers={
                NotificationChannel.IN_APP: InAppNotificationProvider(self.notification_repository),
                NotificationChannel.EMAIL: EmailNotificationProvider(),
                NotificationChannel.PUSH: PushNotificationProvider(),
                NotificationChannel.SMS: SMSNotificationProvider(),
            },
        )

    @cached_property
    def notification_delivery_service(self):
        return NotificationDeliveryService(
            queue=self.notification_queue,
            repository=self.notification_delivery_repository,
        )

    @cached_property
    def notification_service(self):
        return NotificationService(
            repository=self.notification_repository,
            dispatcher=self.notification_dispatcher,
            delivery_service=self.notification_delivery_service,
        )

    @cached_property
    def notification_worker(self):
        return NotificationWorker(
            queue=self.notification_queue,
            dispatcher=self.notification_dispatcher,
            delivery_service=self.notification_delivery_service,
        )

    @cached_property
    def organization_repository(self):
        return OrganizationRepository()

    @cached_property
    def organization_service(self):
        return OrganizationService()

    @cached_property
    def vendor_service(self):
        return VendorService(repository=self.vendor_repository)

    @cached_property
    def member_repository(self):
        return MemberRepository()

    @cached_property
    def member_service(self):
        return MemberService()

    @cached_property
    def income_service(self):
        from app.repositories.finance.finance_repository import IncomeRepository
        return IncomeService(repository=IncomeRepository())

    @cached_property
    def expense_service(self):
        from app.repositories.finance.finance_repository import ExpenseRepository, BudgetRepository
        return ExpenseService(repository=ExpenseRepository(), budget_repository=BudgetRepository())

    @cached_property
    def planning_service(self):
        from app.repositories.finance.finance_repository import RecurringItemRepository, DebtRepository, GoalRepository, AllocationPlanRepository
        return PlanningService(
            recurring_repository=RecurringItemRepository(),
            debt_repository=DebtRepository(),
            goal_repository=GoalRepository(),
            allocation_repository=AllocationPlanRepository(),
        )

    @cached_property
    def finance_worker(self):
        from app.repositories.finance.finance_repository import (
            BudgetRepository,
            RecurringItemRepository,
            GoalRepository,
        )
        return FinanceWorker(
            budget_repository=BudgetRepository(),
            recurring_repository=RecurringItemRepository(),
            goal_repository=GoalRepository(),
            notification_repository=self.notification_repository,
            member_repository=self.member_repository,
            notification_service=self.notification_service,
        )

    @cached_property
    def chat_repository(self):
        return ChatRepository()

    @cached_property
    def search_service(self):
        return SearchService(
            embedding_repository=self.embedding_repository,
            embedding_service=self.embedding_service,
        )

    @cached_property
    def tool_executor(self):
        from app.services.insights.analyzers.vendor_analyzer import VendorAnalyzer
        return ToolExecutor(
            document_repository=self.document_repository,
            vendor_repository=self.vendor_repository,
            organization_repository=OrganizationRepository(),
            search_service=self.search_service,
            income_service=self.income_service,
            expense_service=self.expense_service,
            planning_service=self.planning_service,
            vendor_analyzer=VendorAnalyzer(self.vendor_repository, self.document_repository),
        )

    @cached_property
    def copilot_service(self):
        return CopilotService(
            chat_repository=self.chat_repository,
            search_service=self.search_service,
            tool_executor=self.tool_executor,
        )

    @cached_property
    def approval_workflow_repository(self):
        return ApprovalWorkflowRepository()

    @cached_property
    def approval_step_repository(self):
        return ApprovalStepRepository()

    @cached_property
    def approval_history_repository(self):
        return ApprovalHistoryRepository()

    @cached_property
    def approval_workflow_service(self):
        return ApprovalWorkflowService(self.approval_workflow_repository)

    @cached_property
    def approval_step_service(self):
        return ApprovalStepService(
            self.approval_step_repository,
            audit_service=self.audit_service,
            approval_history_service=self.approval_history_service,
        )

    @cached_property
    def approval_history_service(self):
        return ApprovalHistoryService(self.approval_history_repository)

    @cached_property
    def approval_engine(self):
        return ApprovalEngine(
            workflow_repository=self.approval_workflow_repository,
            step_repository=self.approval_step_repository,
            history_repository=self.approval_history_repository,
        )

    @cached_property
    def approval_worker(self):
        return ApprovalWorker(
            approval_engine=self.approval_engine,
            workflow_service=self.approval_workflow_service,
            step_service=self.approval_step_service,
            history_service=self.approval_history_service,
        )

    @cached_property
    def audit_service(self):
        return AuditService(repository=AuditRepository())

    @cached_property
    def audit_worker(self):
        return AuditWorker(audit_service=self.audit_service)

    @cached_property
    def reminder_worker(self):
        return ReminderWorker(
            step_service=self.approval_step_service,
            step_repository=self.approval_step_repository,
            organization_repository=OrganizationRepository(),
            notification_service=self.notification_service,
        )

    @cached_property
    def escalation_worker(self):
        return EscalationWorker(
            step_service=self.approval_step_service,
            step_repository=self.approval_step_repository,
            organization_repository=OrganizationRepository(),
            notification_service=self.notification_service,
        )

    @cached_property
    def insight_service(self):
        from app.services.insights.analyzers.cashflow_analyzer import CashflowAnalyzer
        from app.services.insights.analyzers.vendor_analyzer import VendorAnalyzer
        from app.services.insights.analyzers.receivable_analyzer import ReceivableAnalyzer
        from app.services.insights.analyzers.payable_analyzer import PayableAnalyzer
        from app.services.insights.analyzers.spending_analyzer import SpendingAnalyzer
        from app.services.insights.analyzers.subscription_analyzer import SubscriptionAnalyzer
        return InsightService(
            notification_service=self.notification_service,
            cashflow_analyzer=CashflowAnalyzer(self.document_repository, PaymentRepository()),
            vendor_analyzer=VendorAnalyzer(self.vendor_repository, self.document_repository),
            receivable_analyzer=ReceivableAnalyzer(self.document_repository),
            payable_analyzer=PayableAnalyzer(self.document_repository),
            spending_analyzer=SpendingAnalyzer(self.document_repository),
            subscription_analyzer=SubscriptionAnalyzer(self.vendor_repository, self.document_repository),
        )

    @cached_property
    def insight_worker(self):
        return InsightWorker(
            insight_service=self.insight_service,
            organization_repository=OrganizationRepository(),
        )

    @cached_property
    def integration_repository(self):
        return IntegrationConnectionRepository()

    @cached_property
    def token_service(self):
        return TokenService(repository=self.integration_repository)

    @cached_property
    def integration_service(self):
        return IntegrationService(
            repository=self.integration_repository,
            quickbooks_oauth=QuickBooksOAuth(),
            xero_oauth=XeroOAuth(),
            token_service=self.token_service,
        )

    @cached_property
    def token_refresh_worker(self):
        return TokenRefreshWorker(
            connection_repository=self.integration_repository,
            member_repository=self.member_repository,
            notification_service=self.notification_service,
            token_service=self.token_service,
        )

    @cached_property
    def quickbooks_worker(self):
        return QuickBooksWorker(sync_service_factory=QuickBooksSyncService, integration_repository=self.integration_repository)

    @cached_property
    def xero_worker(self):
        return XeroWorker(sync_service_factory=XeroSyncService, integration_repository=self.integration_repository)


    @cached_property
    def auth_service(self):
        return AuthService(
            usage_service=UsageService(
                usage_repository=UsageRepository(),
                organization_repository=OrganizationRepository(),
            )
        )

    @cached_property
    def stripe_event_repository(self):
        return StripeEventRepository()

    @cached_property
    def stripe_event_processor(self):
        return StripeEventProcessor(
            events=self.stripe_event_repository,
            organizations=self.organization_repository,
            subscriptions=SubscriptionRepository(),
        )

    @cached_property
    def stripe_billing_service(self):
        return StripeBillingService(
            subscriptions=SubscriptionRepository(),
        )

    @cached_property
    def export_service(self):
        return ExportService()


_container = Container()


def get_container() -> Container:
    return _container
