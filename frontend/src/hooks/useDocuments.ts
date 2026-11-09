"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { documentsApi, exportApi } from "@/api/documents";
import { getErrorMessage } from "@/api/client";
import { useAppStore } from "@/store/useAppStore";

export function useDocuments(industryFilter?: string, query?: string) {
  const [offset, setOffset] = useState(0);
  const limit = 20;
  const ws = useAppStore((s) => s.activeWorkspace?.id);

  useEffect(() => {
    setOffset(0);
  }, [industryFilter, query]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["documents", ws, offset, industryFilter, query],
    queryFn: () => documentsApi.getHistory(offset, limit, industryFilter, query),
    enabled: !!ws,
    staleTime: 0,
    refetchInterval: (query) => {
      const docs = query.state.data?.documents ?? [];
      return docs.some((doc) => ["pending", "processing"].includes(String(doc.capture_status))) ? 1500 : false;
    },
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
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return useQuery({
    queryKey: ["document", ws, invoiceId],
    queryFn: () => documentsApi.getById(invoiceId!),
    enabled: !!ws && !!invoiceId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return useMutation({
    mutationFn: (invoiceId: string) => documentsApi.delete(invoiceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", ws] });
      toast.success("Document deleted.");
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error, "Failed to delete document.")),
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
  const ws = useAppStore((s) => s.activeWorkspace?.id);

  const excelMutation = useMutation({
    mutationFn: (id: string) => exportApi.downloadExcel(id),
    onSuccess: () => toast.success("Excel downloaded!"),
    onError: (error: unknown) => toast.error(getErrorMessage(error, "Excel download failed.")),
  });

  const csvMutation = useMutation({
    mutationFn: (id: string) => exportApi.downloadCsv(id),
    onSuccess: () => toast.success("CSV downloaded!"),
    onError: (error: unknown) => toast.error(getErrorMessage(error, "CSV download failed.")),
  });

  const sheetsMutation = useMutation({
    mutationFn: (id: string) => exportApi.exportToSheets(id),
    onSuccess: (data) => {
      toast.success("Opening Google Sheets...");
      window.open(data.sheets_url, "_blank");
      queryClient.invalidateQueries({ queryKey: ["documents", ws] });
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

export function useDocumentIntelligence(documentId: string | null) {
  const ws = useAppStore((s) => s.activeWorkspace?.id);
  return useQuery({
    queryKey: ["document-intelligence", ws, documentId],
    queryFn: () => documentsApi.getIntelligence(documentId!),
    enabled: !!ws && !!documentId,
    refetchInterval: (query) => {
      const step = query.state.data?.document?.processing_step;
      const ready = query.state.data?.ready;
      const intelligenceStatus = query.state.data?.document?.intelligence_status;
      const captureStatus = query.state.data?.document?.capture_status;
      if (captureStatus === "pending" || captureStatus === "processing") return 1200;
      if (ready || intelligenceStatus === "not_requested" || intelligenceStatus === "complete" || intelligenceStatus === "failed" || step === "capture_complete" || step === "ap_ready") return false;
      return 1500;
    },
    staleTime: 0,
  });
}
