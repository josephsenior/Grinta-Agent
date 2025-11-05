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
        background: "#ef4444",
        color: "#fff",
      },
      iconTheme: {
        primary: "#ef4444",
        secondary: "#fff",
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
        background: "#333",
        color: "#fff",
      },
      iconTheme: {
        primary: "#333",
        secondary: "#fff",
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
        background: "#333",
        color: "#fff",
      },
    });
  },

  info: (msg: string) => {
    const text = normalizeToastMessage(msg);
    safeToast.show(text, {
      position: "top-center",
      className: "bg-background-secondary",

      style: {
        background: "#333",
        color: "#fff",
        lineBreak: "anywhere",
      },
    });
  },
};
