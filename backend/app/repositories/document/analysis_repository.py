"""
============================================================
Analysis Repository

Handles persistence for AI analysis results.

Responsibilities

- AI analysis persistence
- Human review persistence
- Analysis retrieval
- Statistics

Never perform AI reasoning here.
Never calculate scores here.

Business logic belongs in AnalysisService.
============================================================
"""

from app.repositories.base import BaseRepository
from backend.app.core.enum.enums import (
    Recommendation,
    RiskLevel,
)
from datetime import datetime, UTC


class AnalysisRepository(BaseRepository):

    table_name = "document_analyses"

    def table(self):
        return self.db.table(self.table_name)
    
        # =========================================================
    # Creation
    # =========================================================

    async def create_analysis(
        self,
        payload: dict,
    ):
        """
        Persist a completed AI analysis.
        """

        return (
            self.table()
            .insert(payload)
            .execute()
        )

    async def update_analysis(
        self,
        analysis_id: str,
        payload: dict,
    ):
        """
        Update analysis metadata.
        """

        return (
            self.table()
            .update(payload)
            .eq("id", analysis_id)
            .execute()
        )

    async def delete_analysis(
        self,
        analysis_id: str,
    ):
        """
        Delete an analysis.

        Normally only used internally.
        """

        return (
            self.table()
            .delete()
            .eq("id", analysis_id)
            .execute()
        )
    
        # =========================================================
    # Retrieval
    # =========================================================

    async def get_analysis(
        self,
        analysis_id: str,
    ):
        """
        Retrieve an analysis by ID.
        """

        return (
            self.table()
            .select("*")
            .eq("id", analysis_id)
            .single()
            .execute()
        )

    async def get_document_analysis(
        self,
        document_id: str,
    ):
        """
        Retrieve the latest analysis for a document.
        """

        return (
            self.table()
            .select("*")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

    async def list_document_analyses(
        self,
        document_id: str,
    ):
        """
        List all historical analyses for a document.
        """

        return (
            self.table()
            .select("*")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .execute()
        )

    async def list_organization_analyses(
        self,
        org_id: str,
        limit: int = 50,
        offset: int = 0,
    ):
        """
        List analyses for an organization.
        """

        return (
            self.table()
            .select("*", count="exact")
            .eq("org_id", org_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    
        # =========================================================
    # Human Review
    # =========================================================

    async def submit_review(
        self,
        analysis_id: str,
        reviewer_id: str,
        decision: Recommendation,
        override_reason: str | None = None,
    ):
        """
        Persist a human review decision.
        """

        return (
            self.table()
            .update(
                {
                    "reviewed_by": reviewer_id,
                    "reviewed_at": datetime.now(UTC),
                    "final_decision": decision,
                    "override_reason": override_reason,
                }
            )
            .eq("id", analysis_id)
            .execute()
        )

    async def clear_review(
        self,
        analysis_id: str,
    ):
        """
        Remove review metadata.
        """

        return (
            self.table()
            .update(
                {
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "final_decision": None,
                    "override_reason": None,
                }
            )
            .eq("id", analysis_id)
            .execute()
        )
    
        # =========================================================
    # Statistics
    # =========================================================

    async def count_analyses(
        self,
        org_id: str,
    ):
        """
        Count analyses for an organization.
        """

        return (
            self.table()
            .select("id", count="exact")
            .eq("org_id", org_id)
            .execute()
        )

    async def average_health_score(
        self,
        org_id: str,
    ):
        """
        Retrieve health scores for averaging.
        """

        return (
            self.table()
            .select("health_score")
            .eq("org_id", org_id)
            .execute()
        )

    async def risk_distribution(
        self,
        org_id: str,
    ):
        """
        Retrieve risk levels for distribution charts.
        """

        return (
            self.table()
            .select("risk_level")
            .eq("org_id", org_id)
            .execute()
        )

    async def recommendation_distribution(
        self,
        org_id: str,
    ):
        """
        Retrieve recommendation values for analytics.
        """

        return (
            self.table()
            .select("recommendation")
            .eq("org_id", org_id)
            .execute()
        )
    
        # =========================================================
    # Helpers
    # =========================================================

    async def analysis_exists(
        self,
        document_id: str,
    ) -> bool:
        """
        Check whether a document already has at least one analysis.
        """

        response = (
            self.table()
            .select("id", count="exact")
            .eq("document_id", document_id)
            .limit(1)
            .execute()
        )

        return (response.count or 0) > 0

    async def latest_analysis_id(
        self,
        document_id: str,
    ) -> str | None:
        """
        Retrieve the latest analysis ID for a document.
        """

        response = (
            self.table()
            .select("id")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return response.data[0]["id"]

    async def latest_analysis_version(
        self,
        document_id: str,
    ) -> str | None:
        """
        Retrieve the latest analysis version for a document.
        """

        response = (
            self.table()
            .select("analysis_version")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return response.data[0]["analysis_version"]
    
    async def has_human_review( self, analysis_id: str,) -> bool:
            """
            Check whether an analysis has been reviewed by a human.
            """

            response = (
                self.table()
                .select("reviewed_at")
                .eq("id", analysis_id)
                .single()
                .execute()
            )

            return response.data.get("reviewed_at") is not None