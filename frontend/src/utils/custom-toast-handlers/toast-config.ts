import { CSSProperties } from "react";
import type { ToastOptions } from "react-hot-toast";

export const TOAST_STYLE: CSSProperties = {
  background: "var(--bg-primary)",
  border: "1px solid var(--border-primary)",
  color: "var(--text-primary)",
  borderRadius: "12px",
  padding: "16px",
  fontSize: "14px",
  maxWidth: "400px",
};

export const TOAST_OPTIONS: ToastOptions = {
  position: "top-right",
  style: TOAST_STYLE,
};
