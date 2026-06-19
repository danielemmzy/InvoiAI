"use client";
// useExport.ts — hook for all export operations
// Excel, CSV, Google Sheets

import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { exportApi } from "@/api/export";

export function useExport() {
  const queryClient = useQueryClient();

  // Download Excel
  const excelMutation = useMutation({
    mutationFn: (invoiceId: string) => exportApi.downloadExcel(invoiceId),
    onSuccess: () => toast.success("Excel file downloaded!"),
    onError: () => toast.error("Excel download failed. Please try again."),
  });

  // Download CSV
  const csvMutation = useMutation({
    mutationFn: (invoiceId: string) => exportApi.downloadCsv(invoiceId),
    onSuccess: () => toast.success("CSV file downloaded!"),
    onError: () => toast.error("CSV download failed. Please try again."),
  });

  // Export to Google Sheets
  const sheetsMutation = useMutation({
    mutationFn: (invoiceId: string) => exportApi.exportToSheets(invoiceId),
    onSuccess: (data) => {
      toast.success("Opening Google Sheets...");
      window.open(data.sheets_url, "_blank");
      // Refresh document list so sheets_url shows in history
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["document"] });
    },
    onError: (error: unknown) => {
      const msg = getErrorMessage(error);
      if (msg.includes("not connected")) {
        toast.error("Connect your Google account in Settings first.");
      } else {
        toast.error(msg || "Google Sheets export failed.");
      }
    },
  });

  return {
    // Excel
    downloadExcel: (id: string) => excelMutation.mutate(id),
    isDownloadingExcel: excelMutation.isPending,

    // CSV
    downloadCsv: (id: string) => csvMutation.mutate(id),
    isDownloadingCsv: csvMutation.isPending,

    // Sheets
    exportToSheets: (id: string) => sheetsMutation.mutate(id),
    isExportingToSheets: sheetsMutation.isPending,
  };
}

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "response" in error) {
    const e = error as { response?: { data?: { detail?: string } } };
    return e.response?.data?.detail || "";
  }
  return "";
}