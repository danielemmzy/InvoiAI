"use client";

import {
  useCallback,
  useMemo,
  useState,
} from "react";

import {
  useDropzone,
} from "react-dropzone";

import Link from "next/link";

import {
  FileText,
  ReceiptText,
  FileStack,
  ScanLine,
  X,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Upload as UploadIcon,
  Sparkles,
  ArrowRight,
} from "lucide-react";

import DashboardLayout from "@/components/layout/DashboardLayout";

import {
  useUpload,
  useBatchUpload,
} from "@/hooks/useUpload";

import { useIndustries } from "@/hooks/useDocuments";
import { usePlanCatalog } from "@/hooks/useBilling";
import { useAppStore } from "@/store/useAppStore";

import DuplicateUploadDialog from "@/components/documents/DuplicateUploadDialog";

export default function UploadPage() {
  const [
    files,
    setFiles,
  ] = useState<File[]>([]);

  const [
    industry,
    setIndustry,
  ] = useState("general");

  const { data: industries } =
    useIndustries();

  const { data: plans } =
    usePlanCatalog();

  const user =
    useAppStore(
      (state) => state.user
    );

  const uploadProgress =
    useAppStore(
      (state) =>
        state.uploadProgress
    );

  const currentPlan =
    (Array.isArray(plans) ? plans : []).find(
      (plan) =>
        plan.id ===
        (user?.plan || "free")
    );

  const batchLimit =
    currentPlan
      ?.max_batch_upload ?? 1;

  const {
    upload,
    isUploading:
      isSingleUploading,
    duplicate:
      singleDuplicate,
    confirmDuplicate:
      confirmSingleDuplicate,
    cancelDuplicate:
      cancelSingleDuplicate,
  } = useUpload();

  const {
    uploadBatch,
    isUploading:
      isBatchUploading,
    result,
    duplicate:
      batchDuplicate,
    confirmDuplicate:
      confirmBatchDuplicate,
    cancelDuplicate:
      cancelBatchDuplicate,
  } = useBatchUpload();

  const isUploading =
    isSingleUploading ||
    isBatchUploading;

  const duplicate =
    singleDuplicate ||
    batchDuplicate;

  const onDrop =
    useCallback(
      (accepted: File[]) => {
        setFiles(
          (previous) => {
            const combined =
              [
                ...previous,
                ...accepted,
              ];

            if (
              combined.length >
              batchLimit
            ) {
              return combined.slice(
                0,
                batchLimit
              );
            }

            return combined;
          }
        );
      },
      [batchLimit]
    );

  const {
    getRootProps,
    getInputProps,
    isDragActive,
  } = useDropzone({
    onDrop,

    accept: {
      "application/pdf": [
        ".pdf",
      ],
      "image/jpeg": [
        ".jpg",
        ".jpeg",
      ],
      "image/png": [
        ".png",
      ],
      "image/webp": [
        ".webp",
      ],
    },

    maxFiles:
      batchLimit,

    disabled:
      isUploading,
  });

  const removeFile = (
    index: number
  ) => {
    setFiles(
      (previous) =>
        previous.filter(
          (_, i) =>
            i !== index
        )
    );
  };

  const clearFiles = () => {
    if (!isUploading) {
      setFiles([]);
    }
  };

  const atLimit =
    files.length >=
    batchLimit;

  const totalSizeMb =
    useMemo(
      () =>
        files.reduce(
          (
            total,
            file
          ) =>
            total +
            file.size,
          0
        ) /
        1024 /
        1024,
      [files]
    );

  const handleSend =
    () => {
      if (
        !files.length ||
        isUploading
      ) {
        return;
      }

      if (
        files.length === 1
      ) {
        upload({
          file: files[0],
          industry,
          documentType:
            "unknown",
        });

        return;
      }

      uploadBatch({
        files,
        industry,
      });
    };

  /*
   * Single and batch duplicate prompts
   * intentionally have different shapes.
   *
   * Single:
   *   duplicate.file.name
   *
   * Batch:
   *   duplicate.duplicateFiles
   *
   * Keep the resulting dialog data as
   * a simple string[].
   */
  const duplicateNames: string[] =
    singleDuplicate
      ? [
          singleDuplicate.file.name,
        ]
      : batchDuplicate?.duplicateFiles ??
        [];

  return (
    <DashboardLayout>
      <div
        style={{
          maxWidth: 760,
        }}
      >
        <div className="section-label">
          §01 Intake / Universal document inbox
        </div>

        <div className="dash-title serif">
          Send InvoiAI anything.
        </div>

        <div
          className="dash-subtitle"
          style={{
            marginBottom: 24,
          }}
        >
          Invoices, receipts, purchase orders,
          delivery notes, contracts and other
          documents are classified automatically.
          Upload up to {batchLimit} at once on
          your{" "}
          {currentPlan?.display_name ||
            "current"}{" "}
          plan.
        </div>

        <div
          className="dash-grid"
          style={{
            marginBottom: 18,
          }}
        >
          {[
            [
              FileText,
              "Invoice / AP",
            ],
            [
              ReceiptText,
              "Receipt / Expense",
            ],
            [
              FileStack,
              "PO / Procurement",
            ],
            [
              ScanLine,
              "Other documents",
            ],
          ].map(
            ([
              Icon,
              title,
            ]: any) => (
              <div
                className="card"
                style={{
                  padding: 18,
                }}
                key={title}
              >
                <Icon size={20} />

                <div
                  className="card-title"
                  style={{
                    marginTop: 10,
                  }}
                >
                  {title}
                </div>

                <div
                  className="dash-subtitle"
                  style={{
                    fontSize: 12,
                  }}
                >
                  AI routes it to the
                  right workflow.
                </div>
              </div>
            )
          )}
        </div>

        {/* Drop zone */}
        <div
          {...getRootProps()}
          className={`upload-dropzone${
            isDragActive
              ? " active"
              : ""
          }${
            files.length
              ? " has-file"
              : ""
          }${
            atLimit
              ? " at-limit"
              : ""
          }`}
        >
          <input
            {...getInputProps()}
          />

          {files.length === 0 ? (
            <>
              <div className="upload-icon-wrap">
                <UploadIcon
                  size={20}
                />
              </div>

              <div className="upload-title">
                {isDragActive
                  ? "Drop them here"
                  : `Drop up to ${batchLimit} documents here`}
              </div>

              <div className="upload-sub">
                PDF, JPG, PNG or WEBP
                · up to 10MB each
              </div>

              <div className="upload-browse">
                or click to browse files
              </div>
            </>
          ) : (
            <div
              className="upload-file-list"
              onClick={(event) =>
                event.stopPropagation()
              }
            >
              {files.map(
                (
                  file,
                  index
                ) => (
                  <div
                    key={`${file.name}-${index}`}
                    className="upload-file-row"
                  >
                    <FileText
                      size={16}
                    />

                    <div className="upload-file-row-info">
                      <div className="upload-file-row-name">
                        {file.name}
                      </div>

                      <div className="upload-file-row-size">
                        {(
                          file.size /
                          1024 /
                          1024
                        ).toFixed(
                          2
                        )}{" "}
                        MB
                      </div>
                    </div>

                    {!isUploading && (
                      <button
                        className="file-remove"
                        onClick={() =>
                          removeFile(
                            index
                          )
                        }
                        aria-label={`Remove ${file.name}`}
                      >
                        <X
                          size={12}
                        />
                      </button>
                    )}
                  </div>
                )
              )}

              {!atLimit &&
                !isUploading && (
                  <button
                    className="upload-add-more"
                    onClick={(
                      event
                    ) => {
                      event.stopPropagation();

                      (
                        document.querySelector(
                          ".upload-dropzone input"
                        ) as HTMLInputElement
                      )?.click();
                    }}
                  >
                    + Add more (up to{" "}
                    {batchLimit -
                      files.length}{" "}
                    more)
                  </button>
                )}

              {atLimit && (
                <div className="upload-limit-note">
                  Reached your{" "}
                  {currentPlan?.display_name ||
                    "plan"}{" "}
                  limit of{" "}
                  {batchLimit} files
                  per upload.{" "}
                  <Link href="/dashboard/billing">
                    Upgrade for a higher
                    limit →
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Upload progress */}
        {isUploading && (
          <div
            className="card"
            style={{
              padding: 20,
              marginTop: 18,
              border:
                "1px solid #E2DDD4",
              background:
                "#FFFDF9",
            }}
          >
            <div className="flex items-start gap-4">
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
                style={{
                  background:
                    "#F5E6C8",
                  color:
                    "#9A6817",
                }}
              >
                <Loader2
                  size={18}
                  className="animate-spin"
                />
              </div>

              <div className="min-w-0 flex-1">
                <div
                  className="font-medium"
                  style={{
                    color:
                      "#1A1916",
                  }}
                >
                  Receiving your document
                  {files.length > 1
                    ? "s"
                    : ""}
                  …
                </div>

                <div
                  className="mt-1 text-xs leading-5"
                  style={{
                    color:
                      "#6B6860",
                  }}
                >
                  Uploading securely. Once
                  received, the document is stored
                  and ready for your next choice: AI
                  Analysis or AP Automation.
                </div>

                <div
                  className="mt-4 h-1.5 overflow-hidden rounded-full"
                  style={{
                    background:
                      "#E2DDD4",
                  }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.max(
                        5,
                        uploadProgress
                      )}%`,
                      background:
                        "#C8922A",
                    }}
                  />
                </div>

                <div
                  className="mt-2 flex justify-between text-[11px]"
                  style={{
                    color:
                      "#8A867E",
                  }}
                >
                  <span>
                    Secure intake
                  </span>

                  <span>
                    {Math.max(
                      5,
                      uploadProgress
                    )}
                    %
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Summary */}
        {files.length > 0 && (
          <div className="upload-summary-bar">
            <span>
              {files.length} file
              {files.length === 1
                ? ""
                : "s"}{" "}
              ·{" "}
              {totalSizeMb.toFixed(
                1
              )}{" "}
              MB total
            </span>

            <button
              className="upload-clear-all"
              onClick={
                clearFiles
              }
              disabled={
                isUploading
              }
            >
              Clear all
            </button>
          </div>
        )}

        {/* Industry */}
        <label
          className="form-label"
          style={{
            display: "block",
            marginTop: 16,
          }}
        >
          Industry context
          (optional)
        </label>

        <select
          className="finance-input"
          value={industry}
          onChange={(event) =>
            setIndustry(
              event.target.value
            )
          }
          disabled={
            isUploading
          }
        >
          <option value="general">
            General
          </option>

          {(industries || []).map(
            (item) => (
              <option
                key={item.value}
                value={
                  item.value
                }
              >
                {item.label}
              </option>
            )
          )}
        </select>

        {/* Submit */}
        <button
          onClick={
            handleSend
          }
          disabled={
            !files.length ||
            isUploading
          }
          className="btn-primary"
          style={{
            width: "100%",
            marginTop: 18,
            justifyContent:
              "center",
            padding: 14,
          }}
        >
          {isUploading ? (
            <>
              <Loader2
                size={16}
                className="animate-spin"
              />
              Sending to InvoiAI…
            </>
          ) : (
            <>
              Send{" "}
              {files.length > 1
                ? `${files.length} documents`
                : "to InvoiAI"}{" "}
              →
            </>
          )}
        </button>

        {/* Persistent batch results */}
        {result && (
          <div
            className="card"
            style={{
              padding: 20,
              marginTop: 18,
            }}
          >
            <div className="flex items-start gap-3">
              <div
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
                style={{
                  background:
                    "#F5E6C8",
                  color:
                    "#9A6817",
                }}
              >
                <Sparkles
                  size={17}
                />
              </div>

              <div>
                <b
                  style={{
                    color:
                      "#1A1916",
                  }}
                >
                  Processing started
                </b>

                <div
                  className="mt-1 text-xs leading-5"
                  style={{
                    color:
                      "#6B6860",
                  }}
                >
                  {result.accepted} of{" "}
                  {result.total} files
                  were received. Each document is
                  stored and ready for review.
                </div>
              </div>
            </div>

            <div
              className="mt-5"
              style={{
                borderTop:
                  "1px solid #E9E4DA",
              }}
            >
              {result.results.map(
                (item) => (
                  <div
                    key={
                      item.filename
                    }
                    className="flex items-start gap-3 py-3"
                    style={{
                      borderBottom:
                        "1px solid #F0EDE6",
                    }}
                  >
                    {item.status ===
                    "accepted" ? (
                      <CheckCircle2
                        size={15}
                        style={{
                          marginTop: 2,
                          color:
                            "#4C8061",
                          flexShrink: 0,
                        }}
                      />
                    ) : (
                      <AlertTriangle
                        size={15}
                        style={{
                          marginTop: 2,
                          color:
                            "#B87916",
                          flexShrink: 0,
                        }}
                      />
                    )}

                    <div className="min-w-0 flex-1">
                      <div
                        className="truncate text-xs font-medium"
                        style={{
                          color:
                            "#302E29",
                        }}
                        title={
                          item.filename
                        }
                      >
                        {item.filename}
                      </div>

                      <div
                        className="mt-0.5 text-[11px]"
                        style={{
                          color:
                            "#8A867E",
                        }}
                      >
                        {item.status ===
                        "accepted"
                          ? "Received · OCR processing"
                          : item.error ||
                            "Upload requires attention"}
                      </div>
                    </div>
                  </div>
                )
              )}
            </div>

            <div
              className="mt-4 flex items-center gap-2 text-[11px]"
              style={{
                color:
                  "#8A867E",
              }}
            >
              <ArrowRight
                size={13}
              />
              You can continue working.
              Processing continues in
              the background.
            </div>
          </div>
        )}

        {/* Pipeline explanation */}
        <div
          className="card"
          style={{
            padding: 18,
            marginTop: 18,
          }}
        >
          <b>
            What happens next
          </b>

          <div
            className="dash-subtitle"
            style={{
              marginTop: 6,
            }}
          >
            Secure intake → duplicate
            detection → OCR → AI
            classification → workflow
            routing. Each document is
            processed independently in the
            background.
          </div>
        </div>
      </div>

      {/* Duplicate confirmation */}
      <DuplicateUploadDialog
        open={
          Boolean(
            duplicate
          )
        }
        fileNames={
          duplicateNames
        }
        onCancel={() => {
          if (
            singleDuplicate
          ) {
            cancelSingleDuplicate();
            return;
          }

          if (
            batchDuplicate
          ) {
            cancelBatchDuplicate();
          }
        }}
        onConfirm={() => {
          if (
            singleDuplicate
          ) {
            confirmSingleDuplicate();
            return;
          }

          if (
            batchDuplicate
          ) {
            confirmBatchDuplicate();
          }
        }}
        isUploading={
          isUploading
        }
      />
    </DashboardLayout>
  );
}
