"use client";
// ─────────────────────────────────────────────
// useUpload — File upload hook
// Handles the full upload pipeline with progress
// ─────────────────────────────────────────────

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { documentsApi } from "@/api/documents";
import { useAppStore } from "@/store/useAppStore";

export function useUpload() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const setUploadProgress = useAppStore((s) => s.setUploadProgress);

  const mutation = useMutation({
    mutationFn: async ({
      file,
      industry, documentType, financialAccountId,
    }: { file: File; industry: string; documentType?: string; financialAccountId?: string; }) => {
      // Simulate progress for UX feedback
      // Real progress would require XHR with onUploadProgress
      setUploadProgress(5);
      const result = await documentsApi.upload(file, industry, (p) => setUploadProgress(Math.max(5, p)), documentType, financialAccountId);
      setUploadProgress(100);
      return result;
    },
    onSuccess: (data) => {
      setUploadProgress(0);
      // Invalidate history so it refreshes
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["me"] }); // refresh usage count
      toast.success(data.document_type === "bank_statement" ? "Statement received. Transactions are being analyzed." : "Document received. InvoiAI is processing it in the background.");
      // Navigate to result page
      router.push(`/dashboard/document/${data.invoice_id}`);
    },
    onError: (error: unknown) => {
      setUploadProgress(0);
      const msg = getErrorMessage(error) || "Upload failed. Please try again.";
      // Check for plan limit error
      if (msg.includes("Monthly limit")) {
        toast.error("Monthly limit reached. Please upgrade your plan.", {
          duration: 5000,
        });
      } else {
        toast.error(msg);
      }
    },
  });

  return {
    upload: mutation.mutate,
    isUploading: mutation.isPending,
    uploadedDoc: mutation.data,
    uploadError: mutation.error,
    reset: mutation.reset,
  };
}

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "response" in error) {
    const e = error as { response?: { data?: { detail?: string } } };
    return e.response?.data?.detail || "";
  }
  return "";
}

export function useBatchUpload() {
  const queryClient = useQueryClient();
  const setUploadProgress = useAppStore((s) => s.setUploadProgress);

  const mutation = useMutation({
    mutationFn: async ({ files, industry }: { files: File[]; industry: string }) => {
      setUploadProgress(5);
      const result = await documentsApi.uploadBatch(files, industry, (p) => setUploadProgress(Math.max(5, p)));
      setUploadProgress(100);
      return result;
    },
    onSuccess: (data) => {
      setUploadProgress(0);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["me"] });
      if (data.failed === 0) {
        toast.success(`${data.accepted} document${data.accepted === 1 ? "" : "s"} received. Processing in the background.`);
      } else if (data.accepted === 0) {
        toast.error(`All ${data.total} files failed to upload.`);
      } else {
        toast(`${data.accepted} of ${data.total} uploaded. ${data.failed} need another look.`, { icon: "⚠️" });
      }
    },
    onError: (error: unknown) => {
      setUploadProgress(0);
      const msg = getErrorMessage(error) || "Batch upload failed. Please try again.";
      toast.error(msg, { duration: 6000 });
    },
  });

  return {
    uploadBatch: mutation.mutate,
    isUploading: mutation.isPending,
    result: mutation.data,
    error: mutation.error,
    reset: mutation.reset,
  };
}