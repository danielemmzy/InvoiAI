"use client";

import toast from "react-hot-toast";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
} from "lucide-react";

export const showToast = {
  success: (message: string) =>
    toast.success(message, {
      icon: <CheckCircle size={16} color="#C8922A" />,
    }),

  error: (message: string) =>
    toast.error(message, {
      icon: <XCircle size={16} color="#E57373" />,
    }),

  warning: (message: string) =>
    toast(message, {
      icon: <AlertTriangle size={16} color="#C8922A" />,
      style: {
        background: "#1A1916",
        color: "#FFF",
        fontFamily: "'DM Sans', sans-serif",
        fontSize: "13px",
        borderRadius: "8px",
      },
    }),

  info: (message: string) =>
    toast(message, {
      icon: <Info size={16} color="#6B6860" />,
      style: {
        background: "#1A1916",
        color: "#FFF",
        fontFamily: "'DM Sans', sans-serif",
        fontSize: "13px",
        borderRadius: "8px",
      },
    }),

  loading: (message: string) => toast.loading(message),

  dismiss: (id?: string) => toast.dismiss(id),
};

export default showToast;