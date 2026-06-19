"use client";
// Button — reusable button using CSS classes from globals.css

import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "amber" | "ghost" | "danger";
  loading?: boolean;
  children: React.ReactNode;
}

const classMap = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  amber: "btn-amber",
  ghost: "btn-ghost",
  danger: "btn-danger",
};

export default function Button({
  variant = "primary",
  loading = false,
  disabled,
  children,
  style,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={classMap[variant]}
      style={{ opacity: disabled || loading ? 0.5 : 1, cursor: disabled || loading ? "not-allowed" : "pointer", ...style }}
      {...props}
    >
      {loading && <Loader2 size={14} className="animate-spin" />}
      {children}
    </button>
  );
}