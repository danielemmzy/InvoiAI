import io
import csv
import logging
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from app.models.invoice import StructuredDocument

logger = logging.getLogger(__name__)

# ── Styles ────────────────────────────────────────────────────────────────────
HEADER_FILL = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
SECTION_TITLE_FONT = Font(bold=True, size=12, color="1E3A5F")
ALT_ROW_FILL = PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid")


def export_to_excel(doc: StructuredDocument) -> bytes:
    """
    Dynamically generates an Excel file from any StructuredDocument.

    Structure:
      - Sheet 1: Document Summary (document type, industry, totals)
      - One sheet per section GPT extracted
        - dict sections → key/value layout
        - list sections → table layout with headers

    This is fully dynamic — no hardcoded columns anywhere.
    Works for invoices, audit reports, tax returns, anything.
    """
    wb = Workbook()

    # Sheet 1: Summary
    _build_summary_sheet(wb, doc)

    # One sheet per section
    for section_name, section_data in doc.sections.items():
        sheet_title = _to_sheet_title(section_name)

        if isinstance(section_data, list) and section_data:
            _build_table_sheet(wb, sheet_title, section_data)
        elif isinstance(section_data, dict) and section_data:
            _build_keyvalue_sheet(wb, sheet_title, section_data)
        # skip empty sections

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    logger.info(f"Excel export generated — {len(doc.sections)} section sheets")
    return buffer.getvalue()


def export_to_csv(doc: StructuredDocument) -> bytes:
    """
    Exports all sections to a single CSV.
    Each section is separated by a blank row and a section title row.
    List sections get table headers. Dict sections get key/value rows.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Document header
    writer.writerow(["InvoiAI Export"])
    writer.writerow(["Document Type", doc.document_type])
    writer.writerow(["Industry", doc.industry])
    writer.writerow(["Confidence", doc.extraction_confidence or ""])
    writer.writerow([])

    # Totals summary
    if doc.raw_totals:
        writer.writerow(["=== TOTALS ==="])
        for key, value in doc.raw_totals.items():
            writer.writerow([_to_label(key), value])
        writer.writerow([])

    # Each section
    for section_name, section_data in doc.sections.items():
        writer.writerow([f"=== {section_name.upper().replace('_', ' ')} ==="])

        if isinstance(section_data, list) and section_data:
            # Table: headers from first row keys
            if isinstance(section_data[0], dict):
                headers = list(section_data[0].keys())
                writer.writerow([_to_label(h) for h in headers])
                for row in section_data:
                    writer.writerow([row.get(h, "") for h in headers])

        elif isinstance(section_data, dict):
            for key, value in section_data.items():
                writer.writerow([_to_label(key), value if value is not None else ""])

        writer.writerow([])

    logger.info("CSV export generated")
    return buffer.getvalue().encode("utf-8")


# ── Sheet builders ─────────────────────────────────────────────────────────────

def _build_summary_sheet(wb: Workbook, doc: StructuredDocument) -> None:
    """
    First sheet — document metadata and all monetary totals.
    """
    ws = wb.active
    ws.title = "Summary"

    # Document info block
    info_rows = [
        ("Document Type", doc.document_type),
        ("Industry", doc.industry),
        ("Extraction Confidence", doc.extraction_confidence or ""),
        ("Sections Extracted", len(doc.sections)),
    ]

    row = 1
    ws.cell(row=row, column=1, value="DOCUMENT SUMMARY").font = SECTION_TITLE_FONT
    row += 1

    for label, value in info_rows:
        ws.cell(row=row, column=1, value=label).font = Font(bold=True)
        ws.cell(row=row, column=2, value=value)
        row += 1

    row += 1  # blank row

    # Totals block
    if doc.raw_totals:
        ws.cell(row=row, column=1, value="TOTALS").font = SECTION_TITLE_FONT
        row += 1

        # Header
        ws.cell(row=row, column=1, value="Field").fill = HEADER_FILL
        ws.cell(row=row, column=1).font = HEADER_FONT
        ws.cell(row=row, column=2, value="Amount").fill = HEADER_FILL
        ws.cell(row=row, column=2).font = HEADER_FONT
        row += 1

        for key, value in doc.raw_totals.items():
            ws.cell(row=row, column=1, value=_to_label(key))
            ws.cell(row=row, column=2, value=value)
            row += 1

    _set_column_widths(ws, [30, 30])


def _build_table_sheet(wb: Workbook, title: str, data: list) -> None:
    """
    Builds a sheet for list sections (line items, findings, transactions etc.)
    Each item in the list becomes a row. Keys of first item become headers.
    Alternating row colors for readability.
    """
    ws = wb.create_sheet(title=title)

    if not data or not isinstance(data[0], dict):
        return

    # Collect all unique keys across all rows
    # (some rows might have different fields — we handle that)
    all_keys: list[str] = []
    seen = set()
    for row in data:
        for key in row.keys():
            if key not in seen:
                all_keys.append(key)
                seen.add(key)

    # Header row
    for col_idx, key in enumerate(all_keys, start=1):
        cell = ws.cell(row=1, column=col_idx, value=_to_label(key))
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="left")

    # Data rows with alternating fill
    for row_idx, row_data in enumerate(data, start=2):
        fill = ALT_ROW_FILL if row_idx % 2 == 0 else None
        for col_idx, key in enumerate(all_keys, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=row_data.get(key))
            if fill:
                cell.fill = fill

    # Auto-size columns based on content
    _auto_size_columns(ws, all_keys)


def _build_keyvalue_sheet(wb: Workbook, title: str, data: dict) -> None:
    """
    Builds a sheet for dict sections (header info, party details, summary fields).
    Two columns: Field | Value.
    Handles nested dicts as sub-sections.
    """
    ws = wb.create_sheet(title=title)

    # Header
    ws.cell(row=1, column=1, value="Field").fill = HEADER_FILL
    ws.cell(row=1, column=1).font = HEADER_FONT
    ws.cell(row=1, column=2, value="Value").fill = HEADER_FILL
    ws.cell(row=1, column=2).font = HEADER_FONT

    row = 2
    for key, value in data.items():
        if isinstance(value, dict):
            # Nested dict — add a sub-header then expand its fields
            ws.cell(row=row, column=1, value=_to_label(key)).font = Font(bold=True, italic=True)
            row += 1
            for sub_key, sub_value in value.items():
                ws.cell(row=row, column=1, value=f"  {_to_label(sub_key)}")
                ws.cell(row=row, column=2, value=sub_value)
                row += 1
        elif isinstance(value, list):
            # Flatten short lists as comma-separated strings
            ws.cell(row=row, column=1, value=_to_label(key))
            ws.cell(row=row, column=2, value=", ".join(str(v) for v in value))
            row += 1
        else:
            ws.cell(row=row, column=1, value=_to_label(key))
            ws.cell(row=row, column=2, value=value)
            row += 1

    _set_column_widths(ws, [30, 50])


# ── Utilities ─────────────────────────────────────────────────────────────────

def _to_sheet_title(name: str) -> str:
    """
    Converts snake_case section name to a readable Excel sheet title.
    Excel sheet names max 31 chars.
    """
    title = name.replace("_", " ").title()
    return title[:31]


def _to_label(key: str) -> str:
    """Converts snake_case keys to Title Case labels for display."""
    return key.replace("_", " ").title()


def _set_column_widths(ws, widths: list[int]) -> None:
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width


def _auto_size_columns(ws, keys: list[str]) -> None:
    """
    Sets column widths based on header length.
    Capped at 40 chars to prevent absurdly wide columns.
    """
    for i, key in enumerate(keys, start=1):
        width = min(max(len(_to_label(key)) + 4, 12), 40)
        ws.column_dimensions[get_column_letter(i)].width = width