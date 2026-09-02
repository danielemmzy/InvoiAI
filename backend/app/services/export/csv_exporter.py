"""
============================================================
app/services/export/csv_exporter.py

CSV Exporter

Responsibilities
----------------
- Export document to CSV

No database.
No repositories.
============================================================
"""

from __future__ import annotations

import csv
from io import StringIO

from app.models.domain.document import (
    Document,
    DocumentLineItem,
)


class CSVExporter:
    """
    Export documents to CSV.
    """

    def export(
        self,
        *,
        document: Document,
        line_items: list[DocumentLineItem],
    ) -> bytes:

        output = StringIO()

        writer = csv.writer(output)

        # =====================================================
        # Summary
        # =====================================================

        writer.writerow(["Document Summary"])
        writer.writerow([])

        summary = [
            ("Document Number", document.document_number),
            ("Vendor", document.vendor_name),
            ("Document Type", document.document_type.value),
            ("Status", document.status.value),
            ("Currency", document.currency),
            ("Subtotal", document.subtotal),
            ("Tax", document.tax_amount),
            ("Discount", document.discount_amount),
            ("Total", document.total_amount),
            ("Amount Paid", document.amount_paid),
            ("Amount Due", document.amount_due),
            ("Document Date", document.document_date),
            ("Due Date", document.due_date),
        ]

        for key, value in summary:
            writer.writerow([key, value])

        writer.writerow([])
        writer.writerow(["Line Items"])
        writer.writerow([])

        # =====================================================
        # Headers
        # =====================================================

        writer.writerow(
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
        )

        # =====================================================
        # Rows
        # =====================================================

        for item in line_items:

            writer.writerow(
                [
                    item.description,
                    item.quantity,
                    item.unit_price,
                    item.amount,
                    item.tax_amount,
                    item.discount,
                    item.category,
                    item.sku,
                ]
            )

        return output.getvalue().encode("utf-8")