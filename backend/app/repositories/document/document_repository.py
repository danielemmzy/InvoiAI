from __future__ import annotations

from uuid import UUID
from datetime import UTC, datetime, timedelta

from app.core.enum.database import (
    DocumentStatus,
    PipelineStage,
)
from app.mappers.document_mapper import DocumentMapper
from app.models.domain.document import Document
from app.repositories.base import BaseRepository
from app.repositories.mixins.external_sync import ExternalSyncMixin


class DocumentRepository(BaseRepository, ExternalSyncMixin):
    """
    Repository responsible for document persistence.

    Responsibilities
    ----------------
    - Document retrieval
    - Duplicate detection
    - Listing & filtering
    - Pipeline state persistence

    No business logic.
    """

    table_name = "documents"

    mapper = DocumentMapper

    # =========================================================
    # Creation
    # =========================================================

    async def create_document(
        self,
        document: Document,
    ) -> Document:

        return await self.create(document)

    # =========================================================
    # Retrieval
    # =========================================================

    async def get_document(
        self,
        document_id: UUID,
    ) -> Document | None:

        return await self.get(document_id)

    async def get_document_by_number(
        self,
        org_id: UUID,
        document_number: str,
    ) -> Document | None:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("document_number", document_number)
            .limit(1)
            .execute()
        )

        return self._one(response)

    async def get_document_by_hash(
        self,
        org_id: UUID,
        file_hash: str,
        exclude_document_id: UUID | None = None,
    ) -> Document | None:
        """
        Find previous document with same file hash.

        Used by DuplicateCheck.

        exclude_document_id prevents the current
        document from matching itself.
        """

        query = (
            self.table()
            .select("*")
            .eq(
                "org_id",
                str(org_id),
            )
            .eq(
                "file_hash",
                file_hash,
            )
        )

        if exclude_document_id:

            query = query.neq(
                "id",
                str(exclude_document_id),
            )

        response = query.limit(1).execute()

        return self._one(response)

    # =========================================================
    # External Integrations
    # =========================================================

    async def upsert_external(
    self,
    document: Document,
) -> Document:

        existing = await self.get_by_external_id(
            org_id=document.org_id,
            provider=document.provider.value,
            external_id=document.external_id,
        )

        if existing:

            response = (
                self.table()
                .update(
                    self.mapper.to_update(document)
                    | {
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                )
                .eq("id", str(existing.id))
                .execute()
            )

            return self._one(response)

        return await self.create(document)

    async def create_from_integration(
        self,
        document: Document,
    ) -> Document:
        """
        Persist a document originating from an external ERP.
        """

        return await self.create_document(
            document,
        )

    async def update_from_integration(
        self,
        document_id: UUID,
        document: Document,
    ) -> Document | None:
        """
        Update an existing externally-synchronized document.
        """

        return await self.update(
            document_id,
            document,
        )

    async def mark_synced(
        self,
        *,
        document_id: UUID,
    ) -> Document | None:

        response = (
            self.table()
            .update(
                {
                    "last_synced_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    async def mark_external_deleted(
        self,
        *,
        document_id: UUID,
    ) -> Document | None:

        response = (
            self.table()
            .update(
                {
                    "is_archived": True,
                    "archive_reason": "Deleted in external system",
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Listing
    # =========================================================

    async def list_documents(
        self,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("is_archived", False)
            .order(
                "created_at",
                desc=True,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return self._many(response)

    async def list_archived_documents(
        self,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("is_archived", True)
            .order(
                "archived_at",
                desc=True,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return self._many(response)

    async def list_vendor_documents(
        self,
        org_id: UUID,
        vendor_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("vendor_id", str(vendor_id))
            .order(
                "document_date",
                desc=True,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return self._many(response)

    async def list_by_status(
        self,
        org_id: UUID,
        status: DocumentStatus,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("status", status.value)
            .order(
                "created_at",
                desc=True,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return self._many(response)

    async def list_by_pipeline_stage(
        self,
        org_id: UUID,
        stage: PipelineStage,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("pipeline_stage", stage.value)
            .order(
                "created_at",
                desc=True,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Pipeline
    # =========================================================

    async def update_pipeline_stage(
        self,
        document_id: UUID,
        stage: PipelineStage,
    ) -> Document | None:

        response = (
            self.table()
            .update(
                {
                    "pipeline_stage": stage.value,
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    async def update_document_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
    ) -> Document | None:
        """
        Added: this was already being called by AnalysisService but
        did not exist on this repository, so every call to
        analyze_document() would raise AttributeError. DocumentStatus
        has no COMPLETED member (see core/enum/database.py) — use
        APPROVED/REJECTED/NEEDS_REVIEW, matching Flow 3's
        recommendation -> status mapping.
        """

        response = (
            self.table()
            .update(
                {
                    "status": status.value,
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    async def mark_completed(
        self,
        document_id: UUID,
    ) -> Document | None:
        """
        NOTE: fixed — DocumentStatus.COMPLETED and
        PipelineStage.COMPLETED do not exist in core/enum/database.py
        (this call previously raised AttributeError). Using APPROVED /
        PipelineStage.COMPLETE (no trailing D) instead.
        """

        response = (
            self.table()
            .update(
                {
                    "status": DocumentStatus.APPROVED.value,
                    "pipeline_stage": PipelineStage.COMPLETE.value,
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    async def mark_failed(
        self,
        document_id: UUID,
        error_message: str,
    ) -> Document | None:

        response = (
            self.table()
            .update(
                {
                    "status": DocumentStatus.FAILED.value,
                    "pipeline_stage": PipelineStage.FAILED.value,
                    "error_message": error_message,
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    async def increment_retry(
        self,
        document_id: UUID,
    ) -> Document | None:
        """
        Increment retry count using the database RPC.
        """

        response = self.db.rpc(
            "increment_document_retry",
            {
                "p_document_id": str(document_id),
            },
        ).execute()

        return self._one(response)

    # =========================================================
    # Archive
    # =========================================================

    async def archive_document(
        self,
        document_id: UUID,
        archived_by: UUID,
        reason: str | None = None,
    ) -> Document | None:

        response = (
            self.table()
            .update(
                {
                    "is_archived": True,
                    "archived_by": str(archived_by),
                    "archive_reason": reason,
                    "archived_at": "now()",
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    async def restore_document(
        self,
        document_id: UUID,
    ) -> Document | None:

        response = (
            self.table()
            .update(
                {
                    "is_archived": False,
                    "archived_by": None,
                    "archive_reason": None,
                    "archived_at": None,
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Export
    # =========================================================

    async def update_export(
        self,
        document_id: UUID,
        export_format: str,
        exported_by: UUID,
    ) -> Document | None:

        response = (
            self.table()
            .update(
                {
                    "last_exported_format": export_format,
                    "last_exported_by": str(exported_by),
                    "last_exported_at": "now()",
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Statistics
    # =========================================================

    async def count_documents(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .execute()
        )

        return response.count or 0

    # =========================================================
    # Dashboard Metrics
    # =========================================================

    async def count_completed(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .eq(
                "status",
                DocumentStatus.APPROVED.value,
            )
            .execute()
        )

        return response.count or 0

    async def count_processing(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .in_(
                "status",
                [
                    DocumentStatus.PENDING.value,
                    DocumentStatus.OCR_RUNNING.value,
                    DocumentStatus.OCR_COMPLETE.value,
                    DocumentStatus.ANALYSIS_RUNNING.value,
                    DocumentStatus.IN_APPROVAL.value,
                ],
            )
            .execute()
        )

        return response.count or 0

    async def count_failed(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .eq(
                "status",
                DocumentStatus.FAILED.value,
            )
            .execute()
        )

        return response.count or 0

    async def count_needs_review(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .eq(
                "status",
                DocumentStatus.NEEDS_REVIEW.value,
            )
            .execute()
        )

        return response.count or 0

    async def count_approved(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .eq(
                "status",
                DocumentStatus.APPROVED.value,
            )
            .execute()
        )

        return response.count or 0

    async def count_rejected(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .eq(
                "status",
                DocumentStatus.REJECTED.value,
            )
            .execute()
        )

        return response.count or 0

    async def total_document_amount(
        self,
        org_id: UUID,
    ) -> float:

        response = (
            self.table()
            .select("total_amount")
            .eq("org_id", str(org_id))
            .not_.is_("total_amount", "null")
            .execute()
        )

        return float(
            sum(
                float(row["total_amount"])
                for row in (response.data or [])
                if row.get("total_amount") is not None
            )
        )

    async def total_document_count(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .execute()
        )

        return response.count or 0

    # =========================================================
    # Trend Analytics
    # =========================================================

    from datetime import UTC, datetime, timedelta

    async def documents_per_day(
        self,
        org_id: UUID,
        days: int = 30,
    ) -> list[dict]:

        start = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        response = (
            self.table()
            .select("created_at")
            .eq("org_id", str(org_id))
            .gte("created_at", start)
            .order("created_at")
            .execute()
        )

        buckets: dict[str, int] = {}

        for row in response.data or []:
            day = row["created_at"][:10]
            buckets[day] = buckets.get(day, 0) + 1

        return [
            {
                "date": day,
                "count": count,
            }
            for day, count in sorted(buckets.items())
        ]

    async def documents_per_month(
        self,
        org_id: UUID,
        months: int = 12,
    ) -> list[dict]:

        start = (datetime.now(UTC) - timedelta(days=months * 31)).isoformat()

        response = (
            self.table()
            .select("created_at")
            .eq("org_id", str(org_id))
            .gte("created_at", start)
            .order("created_at")
            .execute()
        )

        buckets: dict[str, int] = {}

        for row in response.data or []:
            month = row["created_at"][:7]
            buckets[month] = buckets.get(month, 0) + 1

        return [
            {
                "month": month,
                "count": count,
            }
            for month, count in sorted(buckets.items())
        ]

    async def spending_per_month(
        self,
        org_id: UUID,
        months: int = 12,
    ) -> list[dict]:

        start = (datetime.now(UTC) - timedelta(days=months * 31)).isoformat()

        response = (
            self.table()
            .select("created_at,total_amount")
            .eq("org_id", str(org_id))
            .gte("created_at", start)
            .not_.is_("total_amount", "null")
            .order("created_at")
            .execute()
        )

        buckets: dict[str, float] = {}

        for row in response.data or []:

            month = row["created_at"][:7]

            buckets[month] = buckets.get(month, 0.0) + float(row["total_amount"])

        return [
            {
                "month": month,
                "amount": amount,
            }
            for month, amount in sorted(buckets.items())
        ]

    # =========================================================
    # Risk Analytics
    # =========================================================

    async def risk_distribution(
        self,
        org_id: UUID,
    ) -> dict[str, int]:

        response = self.table().select("risk_level").eq("org_id", str(org_id)).execute()

        distribution = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0,
        }

        for row in response.data or []:

            level = row.get("risk_level")

            if level in distribution:
                distribution[level] += 1

        return distribution

    async def duplicate_count(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .eq("is_duplicate", True)
            .execute()
        )

        return response.count or 0

    async def high_risk_documents(
        self,
        org_id: UUID,
        limit: int = 10,
    ) -> list[Document]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .in_(
                "risk_level",
                [
                    "high",
                    "critical",
                ],
            )
            .order(
                "risk_score",
                desc=True,
            )
            .limit(limit)
            .execute()
        )

        return self._many(response)

    async def average_risk_score(
        self,
        org_id: UUID,
    ) -> float:

        response = (
            self.table()
            .select("risk_score")
            .eq("org_id", str(org_id))
            .not_.is_("risk_score", "null")
            .execute()
        )

        scores = [
            float(row["risk_score"])
            for row in (response.data or [])
            if row.get("risk_score") is not None
        ]

        if not scores:
            return 0.0

        return round(
            sum(scores) / len(scores),
            2,
        )

    async def fraud_flag_count(
        self,
        org_id: UUID,
    ) -> int:

        response = (
            self.table()
            .select(
                "id",
                count="exact",
            )
            .eq("org_id", str(org_id))
            .gt("fraud_flags", 0)
            .execute()
        )

        return response.count or 0

    async def documents_requiring_review(
        self,
        org_id: UUID,
    ) -> list[Document]:

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq(
                "status",
                DocumentStatus.NEEDS_REVIEW.value,
            )
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Export
    # =========================================================

    async def update_export(
        self,
        document_id: UUID,
        export_format: str,
        exported_by: UUID,
    ) -> Document | None:

        response = (
            self.table()
            .update(
                {
                    "last_exported_format": export_format,
                    "last_exported_by": str(exported_by),
                    "last_exported_at": "now()",
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Archive
    # =========================================================

    async def archive_document(
        self,
        document_id: UUID,
        archived_by: UUID,
        reason: str | None = None,
    ) -> Document | None:

        response = (
            self.table()
            .update(
                {
                    "is_archived": True,
                    "archived_by": str(archived_by),
                    "archive_reason": reason,
                    "archived_at": "now()",
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    async def restore_document(
        self,
        document_id: UUID,
    ) -> Document | None:

        response = (
            self.table()
            .update(
                {
                    "is_archived": False,
                    "archived_by": None,
                    "archive_reason": None,
                    "archived_at": None,
                }
            )
            .eq("id", str(document_id))
            .execute()
        )

        return self._one(response)

    # =========================================================
    # Retry
    # =========================================================

    async def increment_retry(
        self,
        document_id: UUID,
    ) -> Document | None:

        response = self.db.rpc(
            "increment_document_retry",
            {
                "p_document_id": str(document_id),
            },
        ).execute()

        return self._one(response)

    # =========================================================
    # Related Records
    # =========================================================

    async def get_document_line_items(
        self,
        document_id: UUID,
    ):
        """
        Retrieve all line items belonging to a document.
        """

        response = (
            self.db.table("document_line_items")
            .select("*")
            .eq("document_id", str(document_id))
            .order("position")
            .execute()
        )

        return response.data or []

    async def get_vendor(
        self,
        vendor_id: UUID,
    ):
        """
        Retrieve the vendor associated with a document.
        """

        response = (
            self.db.table("vendors")
            .select("*")
            .eq("id", str(vendor_id))
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return response.data[0]


    # =========================================================
    # Duplicate Detection
    # =========================================================

    async def find_duplicate(
        self,
        *,
        org_id: UUID,
        document: Document,
    ) -> Document | None:
        """
        Find the most likely duplicate document.

        Priority

        1. File hash
        2. Invoice number
        3. Vendor + amount + invoice date
        """

        #
        # File hash
        #

        if document.file_hash:

            duplicate = await self.get_document_by_hash(
                org_id=org_id,
                file_hash=document.file_hash,
                exclude_document_id=document.id,
            )

            if duplicate:
                return duplicate

        #
        # Invoice number
        #

        if document.document_number:

            duplicate = await self.get_document_by_number(
                org_id=org_id,
                document_number=document.document_number,
            )

            if duplicate and duplicate.id != document.id:
                return duplicate

        #
        # Vendor + Amount + Date
        #

        if document.vendor_id and document.total_amount and document.document_date:

            response = (
                self.table()
                .select("*")
                .eq("org_id", str(org_id))
                .eq("vendor_id", str(document.vendor_id))
                .eq("total_amount", document.total_amount)
                .eq("document_date", document.document_date.isoformat())
                .neq("id", str(document.id))
                .limit(1)
                .execute()
            )

            duplicate = self._one(response)

            if duplicate:
                return duplicate

        return None

    async def list_possible_duplicates(
        self,
        *,
        org_id: UUID,
        vendor_id: UUID,
        amount,
        days: int = 30,
    ):
        """
        Returns documents from the same vendor
        with the same amount in a configurable time window.
        """

        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        response = (
            self.table()
            .select("*")
            .eq("org_id", str(org_id))
            .eq("vendor_id", str(vendor_id))
            .eq("total_amount", amount)
            .gte("document_date", cutoff)
            .order("document_date", desc=True)
            .execute()
        )

        return self._many(response)

    # =========================================================
    # Background work queues
    # =========================================================

    async def list_pending_ocr(self, *, limit: int = 100) -> list[Document]:
        response = (
            self.table()
            .select("*")
            .eq("status", DocumentStatus.PENDING.value)
            .order("created_at")
            .limit(limit)
            .execute()
        )
        return self._many(response)

    async def list_pending_analysis(self, *, limit: int = 100) -> list[Document]:
        response = (
            self.table()
            .select("*")
            .eq("status", DocumentStatus.OCR_COMPLETE.value)
            .order("updated_at")
            .limit(limit)
            .execute()
        )
        return self._many(response)

    # =========================================================
    # Insight projections
    # =========================================================

    async def list_documents_for_spending(
        self,
        *,
        org_id: UUID,
        start_date: str,
        statuses: tuple[DocumentStatus, ...] = (
            DocumentStatus.APPROVED,
            DocumentStatus.NEEDS_REVIEW,
        ),
    ) -> list[dict]:
        """Return the minimal document projection required by spending insights."""
        response = (
            self.table()
            .select("id, document_date")
            .eq("org_id", str(org_id))
            .in_("status", [status.value for status in statuses])
            .gte("document_date", start_date)
            .execute()
        )
        return self.raw_many(response)

    async def list_line_items_for_documents(
        self,
        *,
        document_ids: list[UUID | str],
    ) -> list[dict]:
        """Return the minimal line-item projection required by insight analyzers."""
        if not document_ids:
            return []
        response = (
            self.db.table("document_line_items")
            .select("document_id, category, amount")
            .in_("document_id", [str(value) for value in document_ids])
            .execute()
        )
        return self.raw_many(response)

    async def list_documents_for_embedding(
        self,
        *,
        limit: int = 100,
    ) -> list[Document]:
        """Return completed analysis documents for embedding backfill."""
        response = (
            self.table()
            .select("*")
            .in_(
                "status",
                [
                    DocumentStatus.NEEDS_REVIEW.value,
                    DocumentStatus.APPROVED.value,
                    DocumentStatus.REJECTED.value,
                ],
            )
            .order("updated_at", desc=False)
            .limit(limit)
            .execute()
        )
        return self._many(response)
