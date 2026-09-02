"""
============================================================
Cost Calculator

Calculates OpenAI API usage costs.

Responsibilities
----------------
- Prompt token cost
- Completion token cost
- Total request cost

No OpenAI calls.

No repositories.

No business logic.
============================================================
"""

from __future__ import annotations

from decimal import Decimal


class CostCalculator:
    """
    Calculates OpenAI request costs.

    Prices are USD per 1M tokens.
    """

    PRICING: dict[str, dict[str, Decimal]] = {
        "gpt-4.1-mini": {
            "input": Decimal("0.40"),
            "output": Decimal("1.60"),
        },
        "gpt-4.1": {
            "input": Decimal("2.00"),
            "output": Decimal("8.00"),
        },
        "gpt-4o-mini": {
            "input": Decimal("0.15"),
            "output": Decimal("0.60"),
        },
    }

    # =====================================================
    # Helpers
    # =====================================================

    @classmethod
    def model_pricing(
        cls,
        model: str,
    ) -> dict[str, Decimal]:

        return cls.PRICING.get(
            model,
            {
                "input": Decimal("0"),
                "output": Decimal("0"),
            },
        )

    # =====================================================
    # Cost Calculation
    # =====================================================

    @classmethod
    def calculate(
        cls,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Decimal:

        pricing = cls.model_pricing(model)

        prompt_cost = (
            Decimal(prompt_tokens)
            / Decimal("1000000")
        ) * pricing["input"]

        completion_cost = (
            Decimal(completion_tokens)
            / Decimal("1000000")
        ) * pricing["output"]

        return (
            prompt_cost + completion_cost
        ).quantize(
            Decimal("0.00000001")
        )

    # =====================================================
    # Usage Helper
    # =====================================================

    @classmethod
    def from_usage(
        cls,
        *,
        model: str,
        usage: dict,
    ) -> Decimal:

        return cls.calculate(
            model=model,
            prompt_tokens=usage.get(
                "prompt_tokens",
                0,
            ),
            completion_tokens=usage.get(
                "completion_tokens",
                0,
            ),
        )