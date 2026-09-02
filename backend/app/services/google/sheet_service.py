"""
============================================================
app/services/google/sheets_service.py

Google Sheets Service

Responsibilities
----------------
- Create spreadsheets
- Write summary
- Write line items

No business logic.
============================================================
"""

from __future__ import annotations

from googleapiclient.discovery import build

from app.models.domain.document import (
    Document,
    DocumentLineItem,
)

from app.services.google.credentials import GoogleCredentials


class SheetsService:
    """
    Google Sheets API wrapper.
    """

    def __init__(self) -> None:

        self.client = build(
            "sheets",
            "v4",
            credentials=GoogleCredentials.create(),
        )

    # ======================================================
    # Spreadsheet
    # ======================================================

    async def create_spreadsheet(
        self,
        *,
        title: str,
    ) -> tuple[str, str]:
        """
        Create a spreadsheet.

        Returns
        -------
        (spreadsheet_id, spreadsheet_url)
        """

        spreadsheet = (
            self.client.spreadsheets()
            .create(
                body={
                    "properties": {
                        "title": title,
                    }
                }
            )
            .execute()
        )

        spreadsheet_id = spreadsheet["spreadsheetId"]

        spreadsheet_url = (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        )

        return spreadsheet_id, spreadsheet_url

    # ======================================================
    # Summary
    # ======================================================

    async def write_summary(
        self,
        *,
        spreadsheet_id: str,
        document: Document,
    ) -> None:

        values = [
            ["Document Summary"],
            [],
            ["Document Number", document.document_number],
            ["Vendor", document.vendor_name],
            ["Document Type", document.document_type.value],
            ["Currency", document.currency],
            ["Subtotal", str(document.subtotal or "")],
            ["Tax", str(document.tax_amount or "")],
            ["Discount", str(document.discount_amount or "")],
            ["Total", str(document.total_amount or "")],
        ]

        (
            self.client.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range="Summary!A1",
                valueInputOption="RAW",
                body={"values": values},
            )
            .execute()
        )

    # ======================================================
    # Line Items
    # ======================================================

    async def write_line_items(
        self,
        *,
        spreadsheet_id: str,
        line_items: list[DocumentLineItem],
    ) -> None:

        requests = [
            {
                "addSheet": {
                    "properties": {
                        "title": "Line Items",
                    }
                }
            }
        ]

        (
            self.client.spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests},
            )
            .execute()
        )

        values = [
            [
                "Description",
                "Quantity",
                "Unit Price",
                "Amount",
                "Tax",
                "Discount",
                "Category",
                "SKU",
            ]
        ]

        for item in line_items:

            values.append(
                [
                    item.description,
                    str(item.quantity),
                    str(item.unit_price),
                    str(item.amount),
                    str(item.tax_amount or ""),
                    str(item.discount or ""),
                    item.category or "",
                    item.sku or "",
                ]
            )

        (
            self.client.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range="Line Items!A1",
                valueInputOption="RAW",
                body={"values": values},
            )
            .execute()
        )