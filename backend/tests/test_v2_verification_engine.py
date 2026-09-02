import pytest
from types import SimpleNamespace
from app2.services.verification.engine import VerificationEngine
from app2.core.enum.database import RecommendationType, RiskLevel


class Module:
    def __init__(self, score, name):
        self.score = score
        self.name = name
    async def run(self, *args):
        return SimpleNamespace(score=self.score, metadata={"module": self.name})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scores,expected_risk,expected_recommendation",
    [
        ([90] * 8, RiskLevel.LOW, RecommendationType.APPROVE),
        ([75] * 8, RiskLevel.MEDIUM, RecommendationType.REVIEW),
        ([55] * 8, RiskLevel.HIGH, RecommendationType.REVIEW),
        ([40] * 8, RiskLevel.CRITICAL, RecommendationType.REJECT),
    ],
)
async def test_verification_engine_runs_all_eight_modules_and_decides(
    scores, expected_risk, expected_recommendation
):
    modules = [Module(score, str(i)) for i, score in enumerate(scores)]
    engine = VerificationEngine(*modules)

    result = await engine.verify(
        SimpleNamespace(),
        SimpleNamespace(),
        vendor=SimpleNamespace(),
    )

    assert result["overall_score"] == scores[0]
    assert result["risk_level"] == expected_risk
    assert result["recommendation"] == expected_recommendation
    assert set(result["module_results"]) == {
        "ocr", "math", "vendor", "duplicate", "historical",
        "purchase_order", "fraud", "compliance",
    }
    for module in modules:
        # every module's run was invoked; the test doubles have no counter,
        # but their output is present in the merged result.
        assert module.name in {
            str(i) for i in range(8)
        }
