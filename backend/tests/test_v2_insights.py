from app2.services.insights.result import AnalyzerResult
from app2.services.insights.detectors.expense_anomaly_detector import ExpenseAnomalyDetector
from app2.services.insights.detectors.cashflow_detector import CashflowDetector
from app2.services.insights.detectors.overdue_detector import OverdueDetector
from app2.services.insights.detectors.price_increase_detector import PriceIncreaseDetector
from app2.services.insights.detectors.duplicate_charge_detector import DuplicateChargeDetector
from app2.core.enum.insight import InsightSeverity, InsightType


def test_insight_detectors_apply_thresholds():
    assert ExpenseAnomalyDetector().detect(AnalyzerResult("spending", {"top_spike": {"category":"food","increase_pct":21,"current_month_total":121,"average_total":100}}))["severity"] == InsightSeverity.WARNING
    assert CashflowDetector().detect(AnalyzerResult("cashflow", {"cash_runway_days":59}))["severity"] == InsightSeverity.CRITICAL
    assert OverdueDetector().detect(AnalyzerResult("receivable", {"overdue_amount":1000,"overdue_count":2}))["insight_type"] == InsightType.OVERDUE
    assert PriceIncreaseDetector().detect(AnalyzerResult("vendor", {"top_increase": {"vendor_name":"ACME","increase_pct":11,"latest_amount":111,"avg_amount":100}}))["insight_type"] == InsightType.PRICE_INCREASE
    assert DuplicateChargeDetector().detect(AnalyzerResult("subscription", {"subscriptions":[{"monthly_amount":10}] * 4}))["insight_type"] == InsightType.DUPLICATE


def test_insight_detectors_ignore_non_triggering_values():
    assert ExpenseAnomalyDetector().detect(AnalyzerResult("spending", {"top_spike":{"increase_pct":20}})) is None
    assert CashflowDetector().detect(AnalyzerResult("cashflow", {"cash_runway_days":60})) is None
    assert OverdueDetector().detect(AnalyzerResult("receivable", {"overdue_amount":0})) is None
    assert PriceIncreaseDetector().detect(AnalyzerResult("vendor", {"top_increase":{"increase_pct":10}})) is None
    assert DuplicateChargeDetector().detect(AnalyzerResult("subscription", {"subscriptions":[{"monthly_amount":10}] * 3})) is None
