"use client";

import { useEffect } from "react";
import {
  AlertTriangle,
  Copy,
  FileText,
  X,
} from "lucide-react";

interface DuplicateUploadDialogProps {
  open: boolean;
  fileNames: string[];
  onCancel: () => void;
  onConfirm: () => void;
  isUploading?: boolean;
}

export default function DuplicateUploadDialog({
  open,
  fileNames,
  onCancel,
  onConfirm,
  isUploading = false,
}: DuplicateUploadDialogProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !isUploading) {
        onCancel();
      }
    };

    window.addEventListener(
      "keydown",
      handleKeyDown
    );

    return () => {
      window.removeEventListener(
        "keydown",
        handleKeyDown
      );
    };
  }, [
    open,
    isUploading,
    onCancel,
  ]);

  if (!open) {
    return null;
  }

  const multiple =
    fileNames.length > 1;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center px-4"
      style={{
        background:
          "rgba(26, 25, 22, 0.42)",
        backdropFilter:
          "blur(6px)",
      }}
      onMouseDown={(event) => {
        if (
          event.target ===
            event.currentTarget &&
          !isUploading
        ) {
          onCancel();
        }
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="duplicate-upload-title"
        className="w-full max-w-md overflow-hidden rounded-2xl"
        style={{
          background: "#FFFDF9",
          border:
            "1px solid #E2DDD4",
          boxShadow:
            "0 24px 80px rgba(26, 25, 22, 0.18)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-start justify-between px-6 pt-6"
        >
          <div
            className="flex items-center gap-3"
          >
            <div
              className="flex h-10 w-10 items-center justify-center rounded-xl"
              style={{
                background:
                  "#F5E6C8",
                color:
                  "#9A6817",
              }}
            >
              <Copy size={18} />
            </div>

            <div>
              <div
                className="text-[11px] font-semibold uppercase tracking-[0.14em]"
                style={{
                  color:
                    "#9A6817",
                }}
              >
                Duplicate detected
              </div>

              <h2
                id="duplicate-upload-title"
                className="mt-1 text-lg font-semibold"
                style={{
                  color:
                    "#1A1916",
                }}
              >
                This file is already here
              </h2>
            </div>
          </div>

          {!isUploading && (
            <button
              type="button"
              onClick={onCancel}
              className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors"
              style={{
                color:
                  "#6B6860",
              }}
              aria-label="Close"
            >
              <X size={17} />
            </button>
          )}
        </div>

        {/* Body */}
        <div className="px-6 pb-6 pt-5">
          <p
            className="text-sm leading-6"
            style={{
              color:
                "#6B6860",
            }}
          >
            {multiple
              ? "These files have already been uploaded to this workspace."
              : "This exact file has already been uploaded to this workspace."}
          </p>

          <div
            className="mt-4 overflow-hidden rounded-xl"
            style={{
              background:
                "#F7F4EE",
              border:
                "1px solid #E9E4DA",
            }}
          >
            {fileNames.map(
              (name, index) => (
                <div
                  key={`${name}-${index}`}
                  className="flex items-center gap-3 px-4 py-3"
                  style={{
                    borderBottom:
                      index <
                      fileNames.length -
                        1
                        ? "1px solid #E9E4DA"
                        : "none",
                  }}
                >
                  <FileText
                    size={16}
                    style={{
                      flexShrink: 0,
                      color:
                        "#9A6817",
                    }}
                  />

                  <span
                    className="min-w-0 truncate text-xs font-medium"
                    style={{
                      color:
                        "#302E29",
                    }}
                    title={name}
                  >
                    {name}
                  </span>
                </div>
              )
            )}
          </div>

          <div
            className="mt-4 flex gap-3 rounded-xl px-4 py-3"
            style={{
              background:
                "#FFF8EA",
              border:
                "1px solid #F1DFC0",
            }}
          >
            <AlertTriangle
              size={16}
              style={{
                flexShrink: 0,
                marginTop: 1,
                color:
                  "#9A6817",
              }}
            />

            <p
              className="text-xs leading-5"
              style={{
                color:
                  "#6B6860",
              }}
            >
              You can upload it again if this
              is intentional. InvoiAI will create
              a new document record and process
              it independently.
            </p>
          </div>

          {/* Actions */}
          <div
            className="mt-6 flex gap-3"
          >
            <button
              type="button"
              disabled={isUploading}
              onClick={onCancel}
              className="flex-1 rounded-xl px-4 py-3 text-sm font-medium transition-all"
              style={{
                background:
                  "#F7F4EE",
                border:
                  "1px solid #E2DDD4",
                color:
                  "#302E29",
                opacity:
                  isUploading
                    ? 0.55
                    : 1,
                cursor:
                  isUploading
                    ? "not-allowed"
                    : "pointer",
              }}
            >
              Keep existing
            </button>

            <button
              type="button"
              disabled={isUploading}
              onClick={onConfirm}
              className="flex-1 rounded-xl px-4 py-3 text-sm font-medium transition-all"
              style={{
                background:
                  "#1A1916",
                color:
                  "#FFFFFF",
                opacity:
                  isUploading
                    ? 0.65
                    : 1,
                cursor:
                  isUploading
                    ? "not-allowed"
                    : "pointer",
              }}
            >
              {isUploading
                ? "Uploading…"
                : "Upload anyway"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
