"""
============================================================
Memory Service

Responsibilities
----------------
- Maintain vendor memory
- Maintain organization memory
- Generate AI summaries
- Refresh embeddings

No FastAPI.
============================================================
"""

from __future__ import annotations
from uuid import UUID

from app.models.domain.embedding import DocumentEmbedding, OrganizationEmbedding, VendorEmbedding
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.domain.organization import Organization
from app.models.domain.vendor import Vendor
from app.repositories.document.document_repository import DocumentRepository
from app.repositories.organization.organization_repository import (
    OrganizationRepository,
)
from app.repositories.document.vendor_repository import VendorRepository
from app.repositories.ai.embedding_repository import EmbeddingRepository
from app.services.embedding_service import EmbeddingService

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
)


class MemoryService:
    """
    AI memory management.
    """

    def __init__(self) -> None:

        self.documents = DocumentRepository()

        self.organizations = OrganizationRepository()

        self.vendors = VendorRepository()

        self.embeddings = EmbeddingService()

    # =====================================================
    # Vendor
    # =====================================================

    async def update_vendor_memory(
        self,
        vendor: Vendor,
    ) -> Vendor:

        summary = await self.generate_vendor_summary(
            vendor,
        )

        embedding = await self.embeddings.vendor_embedding(
            vendor,
        )

        await self.vendors.update(
            vendor.id,
            {
                "ai_summary": summary,
            },
        )

        await self.embedding_repository.save_vendor_embedding(
            {
                "vendor_id": vendor.id,
                "org_id": vendor.org_id,
                "embedding": embedding,
                "source_text": summary,
                "model_used": self.embeddings.MODEL,
            }
        )

        vendor.ai_summary = summary

        return vendor

    # =====================================================
    # Organization
    # =====================================================

    async def update_organization_memory(
        self,
        organization: Organization,
    ) -> Organization:

        summary = await self.generate_org_summary(
            organization,
        )

        embedding = await (
            self.embeddings.organization_embedding(
                organization,
            )
        )

        await self.organizations.update_organization(
            organization.id,
            {
                "features": organization.features,
                "ai_summary": summary,
            },
        )

        await self.embedding_repository.save_organization_embedding(
            {
                "org_id": organization.id,
                "embedding": embedding,
                "source_text": summary,
                "model_used": self.embeddings.MODEL,
            }
        )

        organization.ai_summary = summary

        return organization

    # =====================================================
    # Vendor Summary
    # =====================================================

    async def generate_vendor_summary(
        self,
        vendor: Vendor,
    ) -> str:

        prompt = f"""
Vendor

Name: {vendor.name}

Industry: {vendor.industry}

Category: {vendor.category}

Country: {vendor.country}

Invoice Count: {vendor.invoice_count}

Total Spend: {vendor.total_spend}

Average Spend: {vendor.average_spend}

Largest Invoice: {vendor.largest_amount}

Currencies: {", ".join(vendor.currencies_used)}

Risk Level: {vendor.risk_level}

Fraud Flags: {vendor.fraud_flags}

Preferred: {vendor.is_preferred}

Blocked: {vendor.is_blocked}

Write a concise finance memory describing
this vendor.

Include:

- spending habits
- risk
- behaviour
- payment patterns
- useful future context

Maximum 180 words.
"""

        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "You create financial memory.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        return response.choices[0].message.content.strip()

    # =====================================================
    # Organization Summary
    # =====================================================

    async def generate_org_summary(
        self,
        organization: Organization,
    ) -> str:

        prompt = f"""
Organization

Name: {organization.name}

Industry: {organization.industry}

Company Size: {organization.company_size}

Country: {organization.country}

Currency: {organization.currency}

Plan: {organization.plan}

Write a memory describing this business.

Focus on:

- accounting profile

- purchasing behaviour

- likely finance workflow

- useful AI context

Maximum 180 words.
"""

        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "You create organization memory.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        return response.choices[0].message.content.strip()

   