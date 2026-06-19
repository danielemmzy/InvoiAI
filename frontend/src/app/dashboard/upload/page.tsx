"use client";
// Upload page — /dashboard/upload

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { FileText, X, Loader2, ChevronDown } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useUpload } from "@/hooks/useUpload";
import { useIndustries } from "@/hooks/useDocuments";
import { useAppStore } from "@/store/useAppStore";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [industry, setIndustry] = useState("general");
  const [showDropdown, setShowDropdown] = useState(false);
  const { upload, isUploading } = useUpload();
  const { data: industries } = useIndustries();
  const uploadProgress = useAppStore((s) => s.uploadProgress);

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "image/jpeg": [".jpg", ".jpeg"], "image/png": [".png"], "image/webp": [".webp"] },
    maxFiles: 1,
    disabled: isUploading,
  });

  const selectedLabel = industries?.find((i) => i.value === industry)?.label || "General";

  const handleSubmit = () => {
    if (!file) return;
    upload({ file, industry });
  };

  return (
    <DashboardLayout>
      <div style={{ maxWidth: 600 }}>
        <div className="section-label">§01 Process / Upload</div>
        <div className="dash-title serif" style={{ marginBottom: 4 }}>Upload a document</div>
        <div className="dash-subtitle" style={{ marginBottom: 36 }}>
          Upload any invoice, receipt, or business document. Select the industry
          so the AI knows what fields to look for. Results ready in seconds.
        </div>

        {/* Drop zone */}
        <div
          {...getRootProps()}
          className={`upload-dropzone${isDragActive ? " active" : ""}${file ? " has-file" : ""}`}
        >
          <input {...getInputProps()} />
          {file ? (
            <div className="file-preview">
              <div className="file-icon-wrap">
                <FileText size={24} color="#C8922A" />
              </div>
              <div className="file-name">{file.name}</div>
              <div className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</div>
              <button
                className="file-remove"
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
              >
                <X size={12} /> Remove
              </button>
            </div>
          ) : (
            <>
              <div className="upload-icon-wrap">
                <span style={{ fontSize: 22, color: "#6B6860" }}>↑</span>
              </div>
              <div className="upload-title">
                {isDragActive ? "Drop it here" : "Drop your invoice here"}
              </div>
              <div className="upload-sub">PDF, JPG, PNG or WEBP · up to 10MB</div>
              <div className="upload-browse">or click to browse files</div>
            </>
          )}
        </div>

        {/* Industry dropdown */}
        <div style={{ marginTop: 16, marginBottom: 4 }}>
          <label className="form-label">Select industry</label>
        </div>
        <div className="dropdown-wrap">
          <button className="dropdown-btn" onClick={() => setShowDropdown(!showDropdown)}>
            <span>{selectedLabel}</span>
            <ChevronDown size={15} color="#6B6860" style={{ transform: showDropdown ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
          </button>
          {showDropdown && (
            <div className="dropdown-menu">
              {(industries || []).map((ind) => (
                <button
                  key={ind.value}
                  className={`dropdown-item${industry === ind.value ? " selected" : ""}`}
                  onClick={() => { setIndustry(ind.value); setShowDropdown(false); }}
                >
                  {ind.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Progress */}
        {isUploading && uploadProgress > 0 && (
          <div className="progress-wrap">
            <div className="progress-labels">
              <span>Processing document...</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
            </div>
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!file || isUploading}
          className="btn-primary"
          style={{ width: "100%", marginTop: 20, justifyContent: "center", padding: "14px", fontSize: 15, borderRadius: 10 }}
        >
          {isUploading
            ? <><Loader2 size={16} className="animate-spin" /> Extracting data...</>
            : "Extract structured data →"
          }
        </button>

        {/* Supported formats */}
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-header">
            <span className="card-title">Supported formats</span>
          </div>
          <div style={{ padding: "16px 20px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {[
              { icon: "📄", label: "PDF", desc: "Digital or scanned" },
              { icon: "🖼️", label: "JPEG / JPG", desc: "Phone photos" },
              { icon: "🖼️", label: "PNG", desc: "Screenshots" },
              { icon: "🖼️", label: "WEBP", desc: "Modern format" },
            ].map((f) => (
              <div key={f.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 18 }}>{f.icon}</span>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: "#1A1916" }}>{f.label}</div>
                  <div style={{ fontSize: 11, color: "#6B6860" }}>{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ padding: "10px 20px 14px", borderTop: "0.5px solid #E2DDD4", fontSize: 11, color: "#6B6860" }}>
            Max file size: <strong>10MB</strong> · All files are stored securely and privately.
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}