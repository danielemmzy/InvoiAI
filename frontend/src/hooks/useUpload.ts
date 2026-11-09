"use client";

import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import toast from "react-hot-toast";

import { documentsApi } from "@/api/documents";
import { useAppStore } from "@/store/useAppStore";

/* ============================================================
   TYPES
   ============================================================ */

export type DuplicateUploadPrompt = {
  file: File;
  industry: string;
  documentType?: string;
  financialAccountId?: string;
  message: string;
  existingDocumentId?: string;
  existingFileName?: string;
};

export type BatchDuplicatePrompt = {
  files: File[];
  industry: string;
  message: string;
  duplicateFiles: string[];
};

export type UploadVariables = {
  file: File;
  industry: string;
  documentType?: string;
  financialAccountId?: string;
  allowDuplicate?: boolean;
};

export type BatchUploadVariables = {
  files: File[];
  industry: string;
  allowDuplicate?: boolean;
};

/* ============================================================
   SINGLE UPLOAD RETURN TYPE
   ============================================================ */

export type UseUploadResult = {
  upload: ReturnType<
    typeof useMutation<
      unknown,
      unknown,
      UploadVariables
    >
  >["mutate"];

  isUploading: boolean;

  uploadedDoc:
    | any
    | undefined;

  uploadError:
    | unknown
    | null;

  reset: () => void;

  duplicate:
    | DuplicateUploadPrompt
    | null;

  confirmDuplicate: () => void;

  cancelDuplicate: () => void;
};

/* ============================================================
   BATCH UPLOAD RESPONSE
   ============================================================ */

export type BatchUploadResult = Awaited<
  ReturnType<
    typeof documentsApi.uploadBatch
  >
>;

/* ============================================================
   BATCH UPLOAD RETURN TYPE
   ============================================================ */

export type UseBatchUploadResult = {
  uploadBatch: (
    variables: BatchUploadVariables,
    options?: any,
  ) => void;

  isUploading: boolean;

  result:
    | BatchUploadResult
    | undefined;

  error:
    | unknown
    | null;

  reset: () => void;

  duplicate:
    | BatchDuplicatePrompt
    | null;

  confirmDuplicate: () => void;

  cancelDuplicate: () => void;
};

/* ============================================================
   SINGLE UPLOAD
   ============================================================ */

export function useUpload(): UseUploadResult {
  const router =
    useRouter();

  const queryClient =
    useQueryClient();

  const setUploadProgress =
    useAppStore(
      (state) =>
        state.setUploadProgress,
    );

  const [
    duplicate,
    setDuplicate,
  ] =
    useState<DuplicateUploadPrompt | null>(
      null,
    );

  const mutation =
    useMutation<
      Awaited<
        ReturnType<
          typeof documentsApi.upload
        >
      >,
      unknown,
      UploadVariables
    >({
      mutationFn:
        async ({
          file,
          industry,
          documentType,
          financialAccountId,
          allowDuplicate = false,
        }) => {
          setUploadProgress(5);

          const result =
            await documentsApi.upload(
              file,
              industry,
              (progress) => {
                setUploadProgress(
                  Math.max(
                    5,
                    progress,
                  ),
                );
              },
              documentType,
              financialAccountId,
              allowDuplicate,
            );

          setUploadProgress(100);

          return result;
        },

      onSuccess:
        (data) => {
          setUploadProgress(0);

          setDuplicate(null);

          queryClient.invalidateQueries({
            queryKey: [
              "documents",
            ],
          });

          queryClient.invalidateQueries({
            queryKey: [
              "me",
            ],
          });

          toast.success(
            data.document_type ===
              "bank_statement"
              ? "Statement received. Transactions are being analyzed."
              : "Document received. Review it to choose AI Analysis or AP Automation.",
          );

          router.push("/dashboard/history");
        },

      onError:
        (
          error: unknown,
          variables,
        ) => {
          setUploadProgress(0);

          const details =
            getDuplicateDetails(
              error,
            );

          if (
            details.isDuplicate
          ) {
            setDuplicate({
              file:
                variables.file,

              industry:
                variables.industry,

              documentType:
                variables.documentType,

              financialAccountId:
                variables.financialAccountId,

              message:
                details.message ||
                "This exact file has already been uploaded to your workspace.",

              existingDocumentId:
                details.existingDocumentId,

              existingFileName:
                details.existingFileName,
            });

            return;
          }

          const message =
            getErrorMessage(
              error,
            ) ||
            "Upload failed. Please try again.";

          if (
            message
              .toLowerCase()
              .includes(
                "monthly limit",
              )
          ) {
            toast.error(
              "Monthly limit reached. Please upgrade your plan.",
              {
                duration: 5000,
              },
            );
          } else {
            toast.error(
              message,
            );
          }
        },
    });

  const confirmDuplicate =
    () => {
      if (!duplicate) {
        return;
      }

      const pending =
        duplicate;

      setDuplicate(null);

      mutation.mutate({
        file:
          pending.file,

        industry:
          pending.industry,

        documentType:
          pending.documentType,

        financialAccountId:
          pending.financialAccountId,

        allowDuplicate:
          true,
      });
    };

  const cancelDuplicate =
    () => {
      setDuplicate(null);

      mutation.reset();

      setUploadProgress(0);
    };

  return {
    upload:
      mutation.mutate,

    isUploading:
      mutation.isPending,

    uploadedDoc:
      mutation.data,

    uploadError:
      mutation.error,

    reset:
      mutation.reset,

    duplicate,

    confirmDuplicate,

    cancelDuplicate,
  };
}

/* ============================================================
   BATCH UPLOAD
   ============================================================ */

export function useBatchUpload(): UseBatchUploadResult {
  const router = useRouter();
  const queryClient =
    useQueryClient();

  const setUploadProgress =
    useAppStore(
      (state) =>
        state.setUploadProgress,
    );

  const [
    duplicate,
    setDuplicate,
  ] =
    useState<BatchDuplicatePrompt | null>(
      null,
    );

  const mutation =
    useMutation<
      BatchUploadResult,
      unknown,
      BatchUploadVariables
    >({
      mutationFn:
        async ({
          files,
          industry,
          allowDuplicate = false,
        }) => {
          setUploadProgress(5);

          const result =
            await documentsApi.uploadBatch(
              files,
              industry,
              (progress) => {
                setUploadProgress(
                  Math.max(
                    5,
                    progress,
                  ),
                );
              },
              allowDuplicate,
            );

          setUploadProgress(100);

          return result;
        },

      onSuccess:
        (
          data,
          variables,
        ) => {
          setUploadProgress(0);

          /*
           * A batch request may return 202 while
           * individual files are rejected.
           *
           * Look for duplicate results before
           * clearing the duplicate state.
           */
          const duplicateResults =
            data.results.filter(
              (item) => {
                const error =
                  item.error
                    ?.toLowerCase() ||
                  "";

                return (
                  error.includes(
                    "same file",
                  ) ||
                  error.includes(
                    "already exists",
                  ) ||
                  error.includes(
                    "duplicate",
                  )
                );
              },
            );

          if (
            duplicateResults.length >
              0 &&
            !variables.allowDuplicate
          ) {
            const duplicateNames =
              duplicateResults.map(
                (item) =>
                  item.filename,
              );

            const duplicateFiles =
              variables.files.filter(
                (file) =>
                  duplicateNames.includes(
                    file.name,
                  ),
              );

            setDuplicate({
              files:
                duplicateFiles,

              industry:
                variables.industry,

              message:
                duplicateFiles.length ===
                1
                  ? "This file has already been uploaded to your workspace."
                  : "Some of these files have already been uploaded to your workspace.",

              duplicateFiles:
                duplicateNames,
            });

            return;
          }

          setDuplicate(null);

          queryClient.invalidateQueries({
            queryKey: [
              "documents",
            ],
          });

          queryClient.invalidateQueries({
            queryKey: [
              "me",
            ],
          });

          if (
            data.failed === 0
          ) {
            toast.success(
              `${data.accepted} document${
                data.accepted ===
                1
                  ? ""
                  : "s"
              } received. Opening document history.`,
            );
            router.push("/dashboard/history");
            return;
          }

          if (
            data.accepted === 0
          ) {
            toast.error(
              `All ${data.total} files failed to upload.`,
            );

            return;
          }

          toast(
            `${data.accepted} of ${data.total} uploaded. The completed and loading documents are now in History.`,
            { icon: "⚠️" },
          );
          router.push("/dashboard/history");
        },

      onError:
        (
          error: unknown,
        ) => {
          setUploadProgress(0);

          const details =
            getDuplicateDetails(
              error,
            );

          if (
            details.isDuplicate
          ) {
            /*
             * If the backend rejects the whole
             * batch with a 409, there is no safe
             * way to reconstruct the original
             * File[] from the error object here.
             *
             * Normal batch duplicate handling
             * happens through the 202 result above.
             */
            return;
          }

          const message =
            getErrorMessage(
              error,
            ) ||
            "Batch upload failed. Please try again.";

          toast.error(
            message,
            {
              duration: 6000,
            },
          );
        },
    });

  const confirmDuplicate =
    () => {
      if (!duplicate) {
        return;
      }

      const pending =
        duplicate;

      setDuplicate(null);

      mutation.mutate({
        files:
          pending.files,

        industry:
          pending.industry,

        allowDuplicate:
          true,
      });
    };

  const cancelDuplicate =
    () => {
      setDuplicate(null);

      mutation.reset();

      setUploadProgress(0);
    };

  return {
    uploadBatch:
      mutation.mutate,

    isUploading:
      mutation.isPending,

    result:
      mutation.data,

    error:
      mutation.error,

    reset:
      mutation.reset,

    /*
     * Explicitly exposed so TypeScript
     * cannot lose this property through
     * inference.
     */
    duplicate,

    confirmDuplicate,

    cancelDuplicate,
  };
}

/* ============================================================
   ERROR PARSING
   ============================================================ */

function getErrorMessage(
  error: unknown,
): string {
  if (
    !error ||
    typeof error !==
      "object" ||
    !("response" in error)
  ) {
    return "";
  }

  const response =
    (
      error as {
        response?: {
          data?: {
            detail?:
              | string
              | {
                  message?: string;
                };

            message?: string;
          };
        };
      }
    ).response;

  const data =
    response?.data;

  const detail =
    data?.detail;

  if (
    typeof detail ===
    "string"
  ) {
    return detail;
  }

  if (
    detail &&
    typeof detail ===
      "object" &&
    typeof detail.message ===
      "string"
  ) {
    return detail.message;
  }

  return (
    data?.message ||
    ""
  );
}

/* ============================================================
   DUPLICATE ERROR PARSING
   ============================================================ */

function getDuplicateDetails(
  error: unknown,
): {
  isDuplicate: boolean;
  message?: string;
  existingDocumentId?: string;
  existingFileName?: string;
} {
  if (
    !error ||
    typeof error !==
      "object" ||
    !("response" in error)
  ) {
    return {
      isDuplicate: false,
    };
  }

  const response =
    (
      error as {
        response?: {
          status?: number;

          data?: {
            detail?:
              | string
              | {
                  code?: string;
                  message?: string;
                  existing_document_id?: string;
                  existing_file_name?: string;
                };

            code?: string;
            message?: string;

            existing_document_id?: string;

            existing_file_name?: string;
          };
        };
      }
    ).response;

  const data =
    response?.data;

  const detail =
    data?.detail;

  if (
    response?.status ===
      409 ||
    data?.code ===
      "DUPLICATE_DOCUMENT"
  ) {
    if (
      detail &&
      typeof detail ===
        "object"
    ) {
      return {
        isDuplicate:
          true,

        message:
          detail.message,

        existingDocumentId:
          detail.existing_document_id,

        existingFileName:
          detail.existing_file_name,
      };
    }

    return {
      isDuplicate:
        true,

      message:
        typeof detail ===
        "string"
          ? detail
          : data?.message,

      existingDocumentId:
        data?.existing_document_id,

      existingFileName:
        data?.existing_file_name,
    };
  }

  if (
    typeof detail ===
      "string" &&
    (
      detail
        .toLowerCase()
        .includes(
          "same file",
        ) ||
      detail
        .toLowerCase()
        .includes(
          "already exists",
        ) ||
      detail
        .toLowerCase()
        .includes(
          "duplicate",
        )
    )
  ) {
    return {
      isDuplicate:
        true,

      message:
        detail,
    };
  }

  return {
    isDuplicate:
      false,
  };
}