"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import toast from "react-hot-toast";
import { documentsApi, exportApi } from "@/api/documents";

export function useDocuments(industryFilter?: string) {
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["documents", offset, industryFilter],
    queryFn: () => documentsApi.getHistory(offset, limit, industryFilter),
    staleTime: 30 * 1000,
  });

  return {
    documents: data?.documents ?? [],
    total: data?.count ?? 0,
    isLoading,
    isError,
    refetch,
    offset,
    limit,
    nextPage: () => setOffset((o) => o + limit),
    prevPage: () => setOffset((o) => Math.max(0, o - limit)),
    hasMore: (data?.count ?? 0) > offset + limit,
    hasPrev: offset > 0,
  };
}

export function useDocument(invoiceId: string | null) {
  return useQuery({
    queryKey: ["document", invoiceId],
    queryFn: () => documentsApi.getById(invoiceId!),
    enabled: !!invoiceId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invoiceId: string) => documentsApi.delete(invoiceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Document deleted.");
    },
    onError: () => toast.error("Failed to delete document."),
  });
}

export function useIndustries() {
  return useQuery({
    queryKey: ["industries"],
    queryFn: documentsApi.getIndustries,
    staleTime: Infinity,
    select: (data) => data.industries,
  });
}

export function useExport() {
  const queryClient = useQueryClient();

  const excelMutation = useMutation({
    mutationFn: (id: string) => exportApi.downloadExcel(id),
    onSuccess: () => toast.success("Excel downloaded!"),
    onError: () => toast.error("Excel download failed."),
  });

  const csvMutation = useMutation({
    mutationFn: (id: string) => exportApi.downloadCsv(id),
    onSuccess: () => toast.success("CSV downloaded!"),
    onError: () => toast.error("CSV download failed."),
  });

  const sheetsMutation = useMutation({
    mutationFn: (id: string) => exportApi.exportToSheets(id),
    onSuccess: (data) => {
      toast.success("Opening Google Sheets...");
      window.open(data.sheets_url, "_blank");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error: unknown) => {
      const msg = getErrorMessage(error) || "Sheets export failed.";
      toast.error(msg);
    },
  });

  return {
    downloadExcel: excelMutation.mutate,
    isDownloadingExcel: excelMutation.isPending,
    downloadCsv: csvMutation.mutate,
    isDownloadingCsv: csvMutation.isPending,
    exportToSheets: sheetsMutation.mutate,
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