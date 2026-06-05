import logging
from app.core.config import settings
from app.models.invoice import StructuredDocument

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADER_BG = {"red": 0.118, "green": 0.227, "blue": 0.373}
HEADER_FG = {"red": 1.0, "green": 1.0, "blue": 1.0}
ALT_BG = {"red": 0.941, "green": 0.957, "blue": 0.973}


def is_google_configured() -> bool:
    """
    Checks if Google credentials are set in .env.
    Returns False if any required field is empty.
    Lets us return a clean error instead of crashing.
    """
    return all([
        settings.google_project_id,
        settings.google_private_key,
        settings.google_service_account_email,
    ])


def _get_credentials():
    from google.oauth2 import service_account
    credentials_info = {
        "type": "service_account",
        "project_id": settings.google_project_id,
        "private_key_id": settings.google_private_key_id,
        "private_key": settings.google_private_key.replace("\\n", "\n"),
        "client_email": settings.google_service_account_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=SCOPES,
    )


async def export_to_sheets(
    doc: StructuredDocument,
    user_email: str,
    document_name: str,
) -> str:
    """
    Creates a Google Sheets spreadsheet from a StructuredDocument.
    Shares it with the user's email.
    Returns the spreadsheet URL.

    Raises ValueError if Google credentials are not configured.
    """
    if not is_google_configured():
        raise ValueError("Google Sheets is not configured yet.")

    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    try:
        creds = _get_credentials()
        sheets_service = build("sheets", "v4", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)

        title = f"InvoiAI — {doc.document_type} — {document_name}"[:100]

        spreadsheet = sheets_service.spreadsheets().create(
            body={
                "properties": {"title": title},
                "sheets": _build_sheet_definitions(doc),
            }
        ).execute()

        spreadsheet_id = spreadsheet["spreadsheetId"]
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        logger.info(f"Created spreadsheet: {spreadsheet_id}")

        requests = []
        requests.extend(_build_summary_data(doc, spreadsheet))
        requests.extend(_build_section_data(doc, spreadsheet))
        requests.extend(_build_formatting(doc, spreadsheet))

        if requests:
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests}
            ).execute()

        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": user_email,
            },
            sendNotificationEmail=False,
        ).execute()

        logger.info(f"Sheet shared with {user_email}")
        return spreadsheet_url

    except HttpError as e:
        logger.error(f"Google Sheets API error: {e}")
        raise Exception(f"Google Sheets export failed: {e}")
    except Exception as e:
        logger.error(f"Sheets export failed: {e}")
        raise


def _build_sheet_definitions(doc: StructuredDocument) -> list[dict]:
    sheets = [{"properties": {"title": "Summary", "index": 0}}]
    for i, name in enumerate(doc.sections.keys(), start=1):
        title = name.replace("_", " ").title()[:100]
        sheets.append({"properties": {"title": title, "index": i}})
    return sheets


def _get_sheet_id(spreadsheet: dict, title: str) -> int:
    for sheet in spreadsheet.get("sheets", []):
        if sheet["properties"]["title"] == title:
            return sheet["properties"]["sheetId"]
    return 0


def _build_summary_data(doc: StructuredDocument, spreadsheet: dict) -> list[dict]:
    sheet_id = _get_sheet_id(spreadsheet, "Summary")
    rows = [
        ["DOCUMENT SUMMARY"],
        ["Document Type", doc.document_type],
        ["Industry", doc.industry],
        ["Confidence", doc.extraction_confidence or ""],
        ["Sections", len(doc.sections)],
        [],
    ]
    if doc.raw_totals:
        rows.append(["TOTALS"])
        rows.append(["Field", "Amount"])
        for k, v in doc.raw_totals.items():
            rows.append([k.replace("_", " ").title(), v])

    return [{
        "updateCells": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "startColumnIndex": 0},
            "rows": [{"values": [_cell(val) for val in row]} for row in rows],
            "fields": "userEnteredValue,userEnteredFormat"
        }
    }]


def _build_section_data(doc: StructuredDocument, spreadsheet: dict) -> list[dict]:
    requests = []
    for section_name, section_data in doc.sections.items():
        sheet_title = section_name.replace("_", " ").title()[:100]
        sheet_id = _get_sheet_id(spreadsheet, sheet_title)

        if isinstance(section_data, list) and section_data:
            rows = _list_to_rows(section_data)
        elif isinstance(section_data, dict) and section_data:
            rows = _dict_to_rows(section_data)
        else:
            continue

        requests.append({
            "updateCells": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "startColumnIndex": 0},
                "rows": [{"values": [_cell(val) for val in row]} for row in rows],
                "fields": "userEnteredValue,userEnteredFormat"
            }
        })
    return requests


def _build_formatting(doc: StructuredDocument, spreadsheet: dict) -> list[dict]:
    requests = []
    all_titles = ["Summary"] + [
        name.replace("_", " ").title()[:100]
        for name in doc.sections.keys()
    ]
    for title in all_titles:
        sheet_id = _get_sheet_id(spreadsheet, title)
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": HEADER_BG,
                        "textFormat": {"foregroundColor": HEADER_FG, "bold": True, "fontSize": 11}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        })
        requests.append({
            "autoResizeDimensions": {
                "dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 10}
            }
        })
    return requests


def _list_to_rows(data: list) -> list[list]:
    if not data or not isinstance(data[0], dict):
        return []
    all_keys: list[str] = []
    seen: set = set()
    for row in data:
        for k in row.keys():
            if k not in seen:
                all_keys.append(k)
                seen.add(k)
    rows = [[k.replace("_", " ").title() for k in all_keys]]
    for row in data:
        rows.append([row.get(k, "") for k in all_keys])
    return rows


def _dict_to_rows(data: dict) -> list[list]:
    rows = [["Field", "Value"]]
    for k, v in data.items():
        if isinstance(v, dict):
            rows.append([k.replace("_", " ").title(), ""])
            for sk, sv in v.items():
                rows.append([f"  {sk.replace('_', ' ').title()}", sv])
        elif isinstance(v, list):
            rows.append([k.replace("_", " ").title(), ", ".join(str(i) for i in v)])
        else:
            rows.append([k.replace("_", " ").title(), v if v is not None else ""])
    return rows


def _cell(value) -> dict:
    if value is None or value == "":
        return {"userEnteredValue": {"stringValue": ""}}
    elif isinstance(value, bool):
        return {"userEnteredValue": {"boolValue": value}}
    elif isinstance(value, (int, float)):
        return {"userEnteredValue": {"numberValue": value}}
    else:
        return {"userEnteredValue": {"stringValue": str(value)}}