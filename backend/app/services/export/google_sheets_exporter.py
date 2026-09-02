"""
============================================================
app/services/export/google_sheets_exporter.py

Google Sheets Exporter

Responsibilities
----------------
- Create spreadsheet
- Write summary
- Write line items
- Share spreadsheet
- Return ExportResult

No database.
No repositories.
============================================================
"""

from __future__ import annotations

from app.models.domain.document import (
    Document,
    DocumentLineItem,
)
from app.services.export.export_result import ExportResult
from app.services.google.drive_service import DriveService
from app.services.google.sheet_service import SheetsService


class GoogleSheetsExporter:
    """
    Exports documents to Google Sheets.
    """

    def __init__(self) -> None:
        self.sheets = SheetsService()
        self.drive = DriveService()

    async def export(
        self,
        *,
        document: Document,
        line_items: list[DocumentLineItem],
        email: str,
    ) -> ExportResult:
        """
        Export a document to Google Sheets.

        Parameters
        ----------
        document:
            Document being exported.

        line_items:
            Document line items.

        email:
            User email to share the spreadsheet with.

        Returns
        -------
        ExportResult
        """

        spreadsheet_id, spreadsheet_url = (
            await self.sheets.create_spreadsheet(
                title=document.document_number
                or document.file_name
                or "InvoiAI Export",
            )
        )

        await self.sheets.write_summary(
            spreadsheet_id=spreadsheet_id,
            document=document,
        )

        await self.sheets.write_line_items(
            spreadsheet_id=spreadsheet_id,
            line_items=line_items,
        )

        await self.drive.share_with_user(
            file_id=spreadsheet_id,
            email=email,
        )

        return ExportResult(
            success=True,
            filename=f"{document.file_name}.gsheet",
            file_bytes=None,
            content_type="application/vnd.google-apps.spreadsheet",
            url=spreadsheet_url,
        )