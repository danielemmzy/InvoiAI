"""
============================================================
Vendor Memory Service

Responsibilities
----------------
- Generate AI vendor memory
- Maintain vendor intelligence
- Update AI summary
- Update AI risk explanation
- Stamp model metadata

No SQL.
No Supabase.
Uses repositories only.
============================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from openai import AsyncOpenAI

from app.core.config import settings
from app.repositories.document.vendor_repository import VendorRepository

client = AsyncOpenAI(api_key=settings.openai_api_key)


class VendorMemoryService:
    """
    Maintains AI memory for vendors.
    """

    MODEL = "gpt-4.1-mini"

    def __init__(
        self,
        repository: VendorRepository,
    ) -> None:

        self.repository = repository

    # =====================================================
    # Public
    # =====================================================

    async def update_memory(
        self,
        vendor_id: UUID,
    ):
        """
        Regenerate AI memory for a vendor.
        """

        vendor = await self.repository.get(vendor_id)

        if vendor is None:
            raise ValueError("Vendor not found.")

        prompt = self._build_prompt(vendor)

        response = await client.chat.completions.create(
            model=self.MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AP vendor intelligence engine. "
                        "Produce a concise vendor profile and risk explanation."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        summary = response.choices[0].message.content or ""

        explanation = self._extract_risk(summary)

        update = {
            "ai_summary": summary,
            "ai_risk_explanation": explanation,
            "ai_model_used": self.MODEL,
            "ai_last_updated_at": datetime.now(UTC),
        }

        return await self.repository.update(
            vendor_id,
            update,
        )

    # =====================================================
    # Helpers
    # =====================================================

    def _build_prompt(
        self,
        vendor,
    ) -> str:

        return f"""
Vendor Name:
{vendor.name}

Industry:
{vendor.industry}

Category:
{vendor.category}

Statistics

Invoice Count:
{vendor.invoice_count}

Total Spend:
{vendor.total_spend}

Average Spend:
{vendor.average_spend}

Median Spend:
{vendor.median_spend}

Largest Invoice:
{vendor.largest_amount}

Smallest Invoice:
{vendor.smallest_amount}

Currencies:
{", ".join(vendor.currencies_used)}

Typical Currency:
{vendor.typical_currency}

Average Payment Days:
{vendor.average_payment_days}

Fraud Flags:
{vendor.fraud_flags}

Duplicate Documents:
{vendor.duplicate_count}

Anomalies:
{vendor.anomaly_count}

Risk Score:
{vendor.risk_score}

Risk Level:
{vendor.risk_level}

Preferred:
{vendor.is_preferred}

Verified:
{vendor.is_verified}

Blocked:
{vendor.is_blocked}

Write:

1. Executive summary.
2. Spending behaviour.
3. Payment behaviour.
4. Risk assessment.
5. Relationship recommendation.

Maximum 250 words.
""".strip()

    @staticmethod
    def _extract_risk(
        summary: str,
    ) -> str:
        """
        Lightweight extraction until structured
        AI output is introduced.
        """

        lines = summary.splitlines()

        for line in lines:
            if "risk" in line.lower():
                return line.strip()

        return "No specific AI risk explanation generated."