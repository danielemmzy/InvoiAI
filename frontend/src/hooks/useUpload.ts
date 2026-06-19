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
      industry,
    }: {
      file: File;
      industry: string;
    }) => {
      // Simulate progress for UX feedback
      // Real progress would require XHR with onUploadProgress
      setUploadProgress(20);
      const result = await documentsApi.upload(file, industry);
      setUploadProgress(100);
      return result;
    },
    onSuccess: (data) => {
      setUploadProgress(0);
      // Invalidate history so it refreshes
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["me"] }); // refresh usage count
      toast.success("Document processed successfully!");
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