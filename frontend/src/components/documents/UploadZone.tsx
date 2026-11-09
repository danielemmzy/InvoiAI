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
  const [files, setFiles] = useState<File[]>([]);
  const [industry, setIndustry] = useState("general");

  const { data: industries } = useIndustries();
  const { data: plans } = usePlanCatalog();

  const user = useAppStore(
    (state) => state.user
  );

  const uploadProgress = useAppStore(
    (state) => state.uploadProgress
  );

  const currentPlan = (Array.isArray(plans) ? plans : []).find(
    (plan) =>
      plan.id === (user?.plan || "free")
  );

  const batchLimit =
    currentPlan?.max_batch_upload ?? 1;

  /*
   * SINGLE UPLOAD
   *
   * Keep the hook's existing public API:
   * duplicate
   * confirmDuplicate
   * cancelDuplicate
   */
  const {
    upload,
    isUploading: isSingleUploading,
    duplicate: singleDuplicate,
    confirmDuplicate: confirmSingleDuplicate,
    cancelDuplicate: cancelSingleDuplicate,
  } = useUpload();

  /*
   * BATCH UPLOAD
   *
   * Keep the hook's existing public API.
   */
  const {
    uploadBatch,
    isUploading: isBatchUploading,
    result,
    duplicate: batchDuplicate,
    confirmDuplicate: confirmBatchDuplicate,
    cancelDuplicate: cancelBatchDuplicate,
  } = useBatchUpload();

  const isUploading =
    isSingleUploading ||
    isBatchUploading;

  /*
   * The two duplicate prompt types are intentionally
   * different:
   *
   * Single:
   * {
   *   file: File;
   *   ...
   * }
   *
   * Batch:
   * {
   *   files: File[];
   *   duplicateFiles: string[];
   *   ...
   * }
   *
   * Therefore we do NOT merge them into one ambiguous
   * object and then call duplicate.files.
   */
  const duplicate =
    singleDuplicate ||
    batchDuplicate;

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      setFiles((previous) => {
        const combined = [
          ...previous,
          ...acceptedFiles,
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
      });
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
      "application/pdf": [".pdf"],
      "image/jpeg": [
        ".jpg",
        ".jpeg",
      ],
      "image/png": [".png"],
      "image/webp": [".webp"],
    },

    maxFiles: batchLimit,

    disabled: isUploading,
  });

  const removeFile = (
    index: number
  ) => {
    setFiles((previous) =>
      previous.filter(
        (_, i) => i !== index
      )
    );
  };

  const clearFiles = () => {
    if (!isUploading) {
      setFiles([]);
    }
  };

  const atLimit =
    files.length >= batchLimit;

  const totalSizeMb = useMemo(
    () =>
      files.reduce(
        (total, file) =>
          total + file.size,
        0
      ) /
      1024 /
      1024,
    [files]
  );

  /*
   * Send selected files.
   */
  const handleSend = () => {
    if (
      !files.length ||
      isUploading
    ) {
      return;
    }

    /*
     * One file → normal document upload.
     */
    if (files.length === 1) {
      upload({
        file: files[0],
        industry,
        documentType: "unknown",
      });

      return;
    }

    /*
     * Multiple files → batch endpoint.
     */
    uploadBatch({
      files,
      industry,
    });
  };

  /*
   * Build duplicate names safely.
   *
   * SINGLE DUPLICATE:
   * singleDuplicate.file.name
   *
   * BATCH DUPLICATE:
   * batchDuplicate.duplicateFiles
   */
  const duplicateNames: string[] =
    singleDuplicate
      ? [singleDuplicate.file.name]
      : batchDuplicate?.duplicateFiles ??
        [];

  /*
   * Calculate progress defensively.
   *
   * uploadProgress may be undefined/null
   * depending on the current store state.
   */
  const progress =
    typeof uploadProgress === "number"
      ? Math.max(
          0,
          Math.min(
            100,
            uploadProgress
          )
        )
      : 0;

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

        {/* =====================================================
            INDUSTRY
            ===================================================== */}

        <div
          className="card"
          style={{
            padding: 18,
            marginBottom: 18,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent:
                "space-between",
              gap: 16,
              flexWrap: "wrap",
            }}
          >
            <div>
              <div className="card-title">
                Document context
              </div>

              <div
                className="dash-subtitle"
                style={{
                  fontSize: 12,
                  marginTop: 4,
                }}
              >
                Help InvoiAI route and classify
                your documents accurately.
              </div>
            </div>

            <div
              style={{
                minWidth: 220,
              }}
            >
              <label
                htmlFor="upload-industry"
                className="sr-only"
              >
                Industry
              </label>

              <select
                id="upload-industry"
                value={industry}
                onChange={(event) =>
                  setIndustry(
                    event.target.value
                  )
                }
                disabled={isUploading}
                style={{
                  width: "100%",
                  height: 42,
                  border:
                    "1px solid #DDD6CC",
                  borderRadius: 10,
                  padding:
                    "0 12px",
                  background:
                    "#FFFDF9",
                  color:
                    "#1A1916",
                  outline: "none",
                }}
              >
                <option value="general">
                  General
                </option>

                {industries?.map(
                  (item: any) => {
                    const value =
                      typeof item ===
                      "string"
                        ? item
                        : item.value ||
                          item.slug ||
                          item.id;

                    const label =
                      typeof item ===
                      "string"
                        ? item
                        : item.label ||
                          item.name ||
                          value;

                    return (
                      <option
                        key={value}
                        value={value}
                      >
                        {label}
                      </option>
                    );
                  }
                )}
              </select>
            </div>
          </div>
        </div>

        {/* =====================================================
            DOCUMENT TYPES
            ===================================================== */}

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
            ([Icon, title]: any) => (
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

        {/* =====================================================
            DROP ZONE
            ===================================================== */}

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
                <UploadIcon size={20} />
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
                (file, index) => (
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
                        ).toFixed(2)}{" "}
                        MB
                      </div>
                    </div>

                    {!isUploading && (
                      <button
                        type="button"
                        className="file-remove"
                        onClick={() =>
                          removeFile(
                            index
                          )
                        }
                        aria-label={`Remove ${file.name}`}
                      >
                        <X size={12} />
                      </button>
                    )}
                  </div>
                )
              )}

              {!atLimit &&
                !isUploading && (
                  <button
                    type="button"
                    className="upload-add-more"
                    onClick={(event) => {
                      event.stopPropagation();

                      (
                        document.querySelector(
                          ".upload-dropzone input"
                        ) as HTMLInputElement | null
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

        {/* =====================================================
            SELECTED FILE SUMMARY
            ===================================================== */}

        {files.length > 0 &&
          !isUploading && (
            <div
              style={{
                display: "flex",
                alignItems:
                  "center",
                justifyContent:
                  "space-between",
                gap: 12,
                marginTop: 12,
                padding:
                  "0 2px",
                flexWrap: "wrap",
              }}
            >
              <div
                className="dash-subtitle"
                style={{
                  fontSize: 12,
                }}
              >
                {files.length}{" "}
                {files.length === 1
                  ? "document"
                  : "documents"}{" "}
                selected ·{" "}
                {totalSizeMb.toFixed(
                  2
                )}{" "}
                MB total
              </div>

              <button
                type="button"
                onClick={clearFiles}
                style={{
                  border: 0,
                  background:
                    "transparent",
                  padding: 0,
                  cursor: "pointer",
                  color:
                    "#8B5E16",
                  fontSize: 12,
                }}
              >
                Clear all
              </button>
            </div>
          )}

        {/* =====================================================
            UPLOAD PROGRESS
            ===================================================== */}

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
                  Uploading securely.
                  InvoiAI will classify,
                  extract and route the
                  document automatically.
                </div>

                <div
                  style={{
                    marginTop: 14,
                    height: 6,
                    borderRadius: 999,
                    overflow:
                      "hidden",
                    background:
                      "#EDE7DE",
                  }}
                >
                  <div
                    style={{
                      width: `${progress}%`,
                      height: "100%",
                      borderRadius:
                        999,
                      background:
                        "#9A6817",
                      transition:
                        "width 200ms ease",
                    }}
                  />
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent:
                      "space-between",
                    marginTop: 7,
                    fontSize: 11,
                    color:
                      "#8A867D",
                  }}
                >
                  <span>
                    Processing
                  </span>

                  <span>
                    {progress}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* =====================================================
            SUCCESS
            ===================================================== */}

        {result && !isUploading && (
          <div
            className="card"
            style={{
              padding: 20,
              marginTop: 18,
              border:
                "1px solid #D9E7D9",
              background:
                "#FAFCF8",
            }}
          >
            <div className="flex items-start gap-4">
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
                style={{
                  background:
                    "#E6F1E5",
                  color:
                    "#3D7040",
                }}
              >
                <CheckCircle2
                  size={19}
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
                  Upload received
                </div>

                <div
                  className="mt-1 text-xs leading-5"
                  style={{
                    color:
                      "#6B6860",
                  }}
                >
                  Your document
                  {files.length > 1
                    ? "s are"
                    : " is"}{" "}
                  now in the processing
                  pipeline.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* =====================================================
            ACTIONS
            ===================================================== */}

        <div
          style={{
            display: "flex",
            alignItems:
              "center",
            justifyContent:
              "space-between",
            gap: 16,
            marginTop: 18,
            flexWrap: "wrap",
          }}
        >
          <div
            className="dash-subtitle"
            style={{
              fontSize: 12,
              display: "flex",
              alignItems:
                "center",
              gap: 7,
            }}
          >
            <Sparkles size={14} />
            AI classification included
          </div>

          <button
            type="button"
            onClick={handleSend}
            disabled={
              !files.length ||
              isUploading
            }
            style={{
              display: "inline-flex",
              alignItems:
                "center",
              justifyContent:
                "center",
              gap: 9,
              minHeight: 46,
              padding:
                "0 18px",
              borderRadius: 10,
              border: 0,
              background:
                !files.length ||
                isUploading
                  ? "#D9D4CC"
                  : "#1A1916",
              color: "#FFFFFF",
              cursor:
                !files.length ||
                isUploading
                  ? "not-allowed"
                  : "pointer",
              fontWeight: 600,
              fontSize: 13,
              transition:
                "all 160ms ease",
            }}
          >
            {isUploading ? (
              <>
                <Loader2
                  size={16}
                  className="animate-spin"
                />
                Uploading…
              </>
            ) : (
              <>
                Send to InvoiAI
                <ArrowRight
                  size={16}
                />
              </>
            )}
          </button>
        </div>

        {/* =====================================================
            DUPLICATE DIALOG
            ===================================================== */}

        <DuplicateUploadDialog
          open={Boolean(duplicate)}
          fileNames={duplicateNames}
          onCancel={() => {
            if (singleDuplicate) {
              cancelSingleDuplicate();
              return;
            }

            if (batchDuplicate) {
              cancelBatchDuplicate();
            }
          }}
          onConfirm={() => {
            if (singleDuplicate) {
              confirmSingleDuplicate();
              return;
            }

            if (batchDuplicate) {
              confirmBatchDuplicate();
            }
          }}
          isUploading={isUploading}
        />

        {/* =====================================================
            SECURITY / TRUST NOTE
            ===================================================== */}

        <div
          style={{
            display: "flex",
            alignItems:
              "flex-start",
            gap: 10,
            marginTop: 20,
            padding:
              "12px 14px",
            border:
              "1px solid #E7E0D7",
            borderRadius: 10,
            background:
              "#FCFAF6",
          }}
        >
          <AlertTriangle
            size={15}
            style={{
              marginTop: 1,
              flexShrink: 0,
              color:
                "#9A6817",
            }}
          />

          <div
            style={{
              fontSize: 11,
              lineHeight: 1.6,
              color:
                "#706C64",
            }}
          >
            Upload only documents that
            belong to your workspace.
            InvoiAI securely receives the
            original file before processing
            and extraction begins.
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
