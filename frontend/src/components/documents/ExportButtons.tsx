"use client";
// ExportButtons — full-size export buttons for document detail page

import { Loader2 } from "lucide-react";
import { useExport } from "@/hooks/useExport";

interface ExportButtonsProps {
  invoiceId: string;
  sheetsUrl?: string;
}

export default function ExportButtons({ invoiceId, sheetsUrl }: ExportButtonsProps) {
  const {
    downloadExcel, isDownloadingExcel,
    downloadCsv, isDownloadingCsv,
    exportToSheets, isExportingToSheets,
  } = useExport();

  return (
    <div className="export-buttons">
      <button
        className="export-btn"
        onClick={() => downloadExcel(invoiceId)}
        disabled={isDownloadingExcel}
      >
        {isDownloadingExcel ? <Loader2 size={14} className="animate-spin" /> : "⊞"}
        Download Excel
      </button>

      <button
        className="export-btn"
        onClick={() => downloadCsv(invoiceId)}
        disabled={isDownloadingCsv}
      >
        {isDownloadingCsv ? <Loader2 size={14} className="animate-spin" /> : "≡"}
        Download CSV
      </button>

      {sheetsUrl ? (
        <button
          className="export-btn sheets-open"
          onClick={() => window.open(sheetsUrl, "_blank")}
        >
          ↗ Open in Google Sheets
        </button>
      ) : (
        <button
          className="export-btn sheets"
          onClick={() => exportToSheets(invoiceId)}
          disabled={isExportingToSheets}
        >
          {isExportingToSheets ? <Loader2 size={14} className="animate-spin" /> : "↗"}
          Export to Google Sheets
        </button>
      )}
    </div>
  );
}