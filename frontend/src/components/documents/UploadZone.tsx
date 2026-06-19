"use client";
// ─────────────────────────────────────────────
// UploadZone — drag-and-drop file upload
// ─────────────────────────────────────────────

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, X, Loader2, ChevronDown } from "lucide-react";
import { useUpload } from "@/hooks/useUpload";
import { useIndustries } from "@/hooks/useDocuments";
import { useAppStore } from "@/store/useAppStore";

export default function UploadZone() {
  const [file, setFile] = useState<File | null>(null);
  const [industry, setIndustry] = useState("general");
  const [showIndustries, setShowIndustries] = useState(false);
  const { upload, isUploading } = useUpload();
  const { data: industries } = useIndustries();
  const uploadProgress = useAppStore((s) => s.uploadProgress);

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/webp": [".webp"],
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  const selectedIndustry = industries?.find((i) => i.value === industry);

  const handleSubmit = () => {
    if (!file) return;
    upload({ file, industry });
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className="rounded-xl cursor-pointer transition-all duration-200"
        style={{
          border: `2px dashed ${isDragActive ? "#C8922A" : file ? "#C8922A" : "#E2DDD4"}`,
          background: isDragActive ? "#FFF8F0" : file ? "#FFFDF9" : "#FFFFFF",
          padding: "56px 40px",
          textAlign: "center",
        }}
      >
        <input {...getInputProps()} />

        {file ? (
          <div className="flex flex-col items-center gap-3">
            <div
              className="w-14 h-14 rounded-xl flex items-center justify-center"
              style={{ background: "#F5E6C8" }}
            >
              <FileText size={24} color="#C8922A" />
            </div>
            <div>
              <p className="font-medium text-sm" style={{ color: "#1A1916" }}>
                {file.name}
              </p>
              <p className="text-xs mt-0.5" style={{ color: "#6B6860" }}>
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); }}
              className="flex items-center gap-1 text-xs px-3 py-1 rounded-md"
              style={{ color: "#C0392B", background: "#FDECEA" }}
            >
              <X size={12} />
              Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div
              className="w-14 h-14 rounded-xl flex items-center justify-center"
              style={{ background: "#F7F4EE", border: "0.5px solid #E2DDD4" }}
            >
              <Upload size={22} color="#6B6860" />
            </div>
            <div>
              <p className="font-medium text-sm" style={{ color: "#1A1916" }}>
                {isDragActive ? "Drop it here" : "Drop your invoice here"}
              </p>
              <p className="text-xs mt-1" style={{ color: "#6B6860" }}>
                PDF, JPG, PNG or WEBP · up to 10MB
              </p>
            </div>
            <div
              className="text-xs px-4 py-2 rounded-lg"
              style={{ border: "0.5px solid #E2DDD4", color: "#6B6860" }}
            >
              or click to browse files
            </div>
          </div>
        )}
      </div>

      {/* Industry selector */}
      <div className="mt-4 relative">
        <div className="text-xs font-medium mb-2" style={{ color: "#6B6860" }}>
          Select industry
        </div>
        <button
          onClick={() => setShowIndustries(!showIndustries)}
          className="w-full flex items-center justify-between px-4 py-3 rounded-lg text-sm transition-all"
          style={{
            background: "#FFFFFF",
            border: "0.5px solid #E2DDD4",
            color: "#1A1916",
          }}
        >
          <span>{selectedIndustry?.label || "General"}</span>
          <ChevronDown size={16} color="#6B6860" className={showIndustries ? "rotate-180" : ""} style={{ transition: "transform 0.2s" }} />
        </button>

        {showIndustries && (
          <div
            className="absolute top-full left-0 right-0 mt-1 rounded-lg overflow-auto z-20"
            style={{
              background: "#FFFFFF",
              border: "0.5px solid #E2DDD4",
              boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
              maxHeight: 280,
            }}
          >
            {(industries || []).map((ind) => (
              <button
                key={ind.value}
                onClick={() => { setIndustry(ind.value); setShowIndustries(false); }}
                className="w-full text-left px-4 py-2.5 text-sm transition-all"
                style={{
                  background: industry === ind.value ? "#F7F4EE" : "transparent",
                  color: industry === ind.value ? "#C8922A" : "#1A1916",
                  fontWeight: industry === ind.value ? 500 : 400,
                  borderBottom: "0.5px solid #F0EDE6",
                }}
              >
                {ind.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Progress bar */}
      {isUploading && uploadProgress > 0 && (
        <div className="mt-4">
          <div className="flex justify-between text-xs mb-1.5" style={{ color: "#6B6860" }}>
            <span>Processing document...</span>
            <span>{uploadProgress}%</span>
          </div>
          <div className="h-1.5 rounded-full" style={{ background: "#E2DDD4" }}>
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${uploadProgress}%`, background: "#C8922A" }}
            />
          </div>
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!file || isUploading}
        className="w-full mt-4 py-3.5 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2"
        style={{
          background: !file || isUploading ? "#E2DDD4" : "#1A1916",
          color: !file || isUploading ? "#AAA8A0" : "#FFFFFF",
          cursor: !file || isUploading ? "not-allowed" : "pointer",
        }}
      >
        {isUploading ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Extracting data...
          </>
        ) : (
          "Extract structured data →"
        )}
      </button>
    </div>
  );
}