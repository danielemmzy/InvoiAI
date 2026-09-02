from __future__ import annotations

from googleapiclient.discovery import build

from app.integrations.google.client import GoogleClient


class GoogleSheetsService:
    """
    Google Sheets API wrapper.

    Responsibilities
    ----------------
    • Read spreadsheet data
    • Write spreadsheet data
    • Append rows
    • Create spreadsheets

    No business logic.
    """

    def __init__(
        self,
        *,
        org_id,
    ) -> None:

        self.client = GoogleClient(
            org_id=org_id,
        )

    async def service(self):

        return build(
            "sheets",
            "v4",
            credentials=await self.client.credentials(),
            cache_discovery=False,
        )

    # =====================================================
    # Spreadsheet
    # =====================================================

    async def create_spreadsheet(
        self,
        *,
        title: str,
    ):

        sheets = await self.service()

        spreadsheet = {
            "properties": {
                "title": title,
            }
        }

        return (
            sheets.spreadsheets()
            .create(
                body=spreadsheet,
            )
            .execute()
        )

    # =====================================================
    # Read
    # =====================================================

    async def read_range(
        self,
        *,
        spreadsheet_id: str,
        cell_range: str,
    ):

        sheets = await self.service()

        result = (
            sheets.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=cell_range,
            )
            .execute()
        )

        return result.get(
            "values",
            [],
        )

    # =====================================================
    # Write
    # =====================================================

    async def update_range(
        self,
        *,
        spreadsheet_id: str,
        cell_range: str,
        values: list[list],
    ):

        sheets = await self.service()

        body = {
            "values": values,
        }

        return (
            sheets.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=cell_range,
                valueInputOption="USER_ENTERED",
                body=body,
            )
            .execute()
        )

    async def append_rows(
        self,
        *,
        spreadsheet_id: str,
        sheet_name: str,
        values: list[list],
    ):

        sheets = await self.service()

        body = {
            "values": values,
        }

        return (
            sheets.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=sheet_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )

    # =====================================================
    # Clear
    # =====================================================

    async def clear_range(
        self,
        *,
        spreadsheet_id: str,
        cell_range: str,
    ):

        sheets = await self.service()

        return (
            sheets.spreadsheets()
            .values()
            .clear(
                spreadsheetId=spreadsheet_id,
                range=cell_range,
                body={},
            )
            .execute()
        )