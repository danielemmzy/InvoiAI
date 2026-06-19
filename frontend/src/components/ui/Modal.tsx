"use client";
// Modal — reusable modal dialog

import { useEffect } from "react";
import { X } from "lucide-react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}

export default function Modal({ open, onClose, title, children }: ModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    if (open) document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  if (!open) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 50,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 16, background: "rgba(26,25,22,0.6)", backdropFilter: "blur(4px)",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%", maxWidth: 520, background: "#FFFFFF",
          border: "0.5px solid #E2DDD4", borderRadius: 16, overflow: "hidden",
        }}
      >
        {title && (
          <div className="card-header">
            <span className="serif" style={{ fontSize: 18, fontWeight: 600, color: "#1A1916" }}>{title}</span>
            <button onClick={onClose} className="doc-action-btn"><X size={15} /></button>
          </div>
        )}
        <div style={{ padding: 24 }}>{children}</div>
      </div>
    </div>
  );
}