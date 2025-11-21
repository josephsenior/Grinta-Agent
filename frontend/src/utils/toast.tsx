import safeToast from "#/utils/safe-hot-toast";
import { calculateToastDuration } from "./toast-duration";
import { normalizeToastMessage } from "./toast-normalize";

const idMap = new Map<string, string>();

export default {
  error: (id: string, msg: string) => {
    if (idMap.has(id)) {
      return;
    } // prevent duplicate toast
    const text = normalizeToastMessage(msg);
    const toastId = safeToast.show(text, {
      duration: 4000,
      style: {
        background: "var(--bg-primary)",
        color: "var(--text-primary)",
        border: "1px solid var(--text-danger)",
        borderRadius: "12px",
        padding: "16px",
        fontSize: "14px",
        maxWidth: "400px",
      },
      iconTheme: {
        primary: "var(--text-danger)",
        secondary: "var(--text-primary)",
      },
    });
    idMap.set(id, String(toastId));
  },
  success: (id: string, msg: string, duration: number = 4000) => {
    if (idMap.has(id)) {
      return;
    } // prevent duplicate toast
    const text = normalizeToastMessage(msg);
    const toastId = safeToast.success(text, {
      duration,
      style: {
        background: "var(--bg-primary)",
        color: "var(--text-primary)",
        border: "1px solid var(--text-success)",
        borderRadius: "12px",
        padding: "16px",
        fontSize: "14px",
        maxWidth: "400px",
      },
      iconTheme: {
        primary: "var(--text-success)",
        secondary: "var(--text-primary)",
      },
    });
    idMap.set(id, String(toastId));
  },
  settingsChanged: (msg: string) => {
    const text = normalizeToastMessage(msg);
    safeToast.show(text, {
      position: "bottom-right",
      className: "bg-background-secondary",
      duration: calculateToastDuration(msg, 5000),
      icon: "⚙️",
      style: {
        background: "var(--bg-primary)",
        color: "var(--text-primary)",
        border: "1px solid var(--border-primary)",
        borderRadius: "12px",
        padding: "16px",
        fontSize: "14px",
        maxWidth: "400px",
      },
    });
  },

  info: (msg: string) => {
    const text = normalizeToastMessage(msg);
    safeToast.show(text, {
      position: "top-center",
      className: "bg-background-secondary",
      style: {
        background: "#000",
        color: "#fff",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        borderRadius: "12px",
        padding: "16px",
        fontSize: "14px",
        maxWidth: "400px",
        lineBreak: "anywhere",
      },
    });
  },
};
