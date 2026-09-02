"""
============================================================
app/services/export/export_service.py

Export Service

Responsibilities
----------------
- Export documents
- Retrieve document data
- Delegate to exporters
- Persist export history

No FastAPI.
No business logic.
============================================================
"""

from __future__ import annotations

from uuid import UUID

from app.repositories.document.document_repository import DocumentRepository
from app.services.export.csv_exporter import CSVExporter
from app.services.export.excel_exporter import ExcelExporter
from app.services.export.google_sheets_exporter import GoogleSheetsExporter
from app.services.export.export_result import ExportResult


class ExportService:
    """
    Handles all document exports.
    """

    def __init__(self) -> None:

        self.documents = DocumentRepository()

        self.excel = ExcelExporter()

        self.csv = CSVExporter()

        self.sheets = GoogleSheetsExporter()

    # =====================================================
    # Generic Export
    # =====================================================

    async def export(
        self,
        *,
        document_id: UUID,
        exported_by: UUID,
        export_format: str,
    ) -> ExportResult:

        document = await self.documents.get_document(
            document_id,
        )

        if not document:

            raise ValueError("Document not found.")

        line_items = await self.documents.get_document_line_items(
            document_id,
        )

        if export_format == "excel":

            result = await self.export_excel(
                document_id=document_id,
            )

        elif export_format == "csv":

            result = await self.export_csv(
                document_id=document_id,
            )

        elif export_format == "google_sheets":

            result = await self.export_google_sheets(
                document_id=document_id,
            )

        else:

            raise ValueError(
                f"Unsupported export format '{export_format}'."
            )

        await self.documents.update_export(
            document_id=document_id,
            export_format=export_format,
            exported_by=exported_by,
        )

        return result

    # =====================================================
    # Excel
    # =====================================================

    async def export_excel(
        self,
        *,
        document_id: UUID,
    ) -> ExportResult:

        document = await self.documents.get_document(
            document_id,
        )

        if not document:

            raise ValueError("Document not found.")

        line_items = await self.documents.get_document_line_items(
            document_id,
        )

        data = self.excel.export(
            document=document,
            line_items=line_items,
        )

        return ExportResult(
            success=True,
            file_bytes=data,
            filename=f"{document.file_name}.xlsx",
            content_type=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

    # =====================================================
    # CSV
    # =====================================================

    async def export_csv(
        self,
        *,
        document_id: UUID,
    ) -> ExportResult:

        document = await self.documents.get_document(
            document_id,
        )

        if not document:

            raise ValueError("Document not found.")

        line_items = await self.documents.get_document_line_items(
            document_id,
        )

        data = self.csv.export(
            document=document,
            line_items=line_items,
        )

        return ExportResult(
            success=True,
            file_bytes=data,
            filename=f"{document.file_name}.csv",
            content_type="text/csv",
        )

    # =====================================================
    # Google Sheets
    # =====================================================

    async def export_google_sheets(
        self,
        *,
        document_id: UUID,
    ) -> ExportResult:

        document = await self.documents.get_document(
            document_id,
        )

        if not document:

            raise ValueError("Document not found.")

        line_items = await self.documents.get_document_line_items(
            document_id,
        )

        url = await self.sheets.export(
            document=document,
            line_items=line_items,
        )

        return ExportResult(
            success=True,
            url=url,
        )