import React, { useEffect, useState } from "react";
import safeToast from "#/utils/safe-hot-toast";
import { logger } from "#/utils/logger";

// Client-only Toaster loader that does NOT import react-hot-toast
// directly. Instead we rely on the safe wrapper's `raw` field to
// expose the real library once it has loaded. This prevents importing
// the third-party bundle during hydration/SSR which previously caused
// an import-time TypeError in the goober runtime.
interface ToasterProps {
  position?: string;
  toastOptions?: {
    duration?: number;
    style?: React.CSSProperties;
    success?: {
      iconTheme?: {
        primary?: string;
        secondary?: string;
      };
      style?: React.CSSProperties;
    };
    error?: {
      iconTheme?: {
        primary?: string;
        secondary?: string;
      };
      style?: React.CSSProperties;
    };
  };
}

export default function ToasterClient(): React.ReactElement | null {
  const [Toaster, setToaster] =
    useState<React.ComponentType<ToasterProps> | null>(null);

  useEffect(() => {
    let mounted = true;

    // If the safe wrapper has already loaded the real library, use it.
    const holder = safeToast as unknown;
    const raw =
      typeof holder === "object" &&
      holder !== null &&
      "raw" in (holder as Record<string, unknown>)
        ? (holder as Record<string, unknown>).raw
        : undefined;

    if (raw) {
      const m = raw as Record<string, unknown>;
      const { Toaster: ToasterComp, default: defaultExport } = m;
      const comp =
        ToasterComp ||
        (defaultExport &&
          (defaultExport as Record<string, unknown>)?.Toaster) ||
        (defaultExport as React.ComponentType);
      if (comp && mounted) {
        setToaster(() => comp as React.ComponentType<ToasterProps>);
      }
      return () => {
        mounted = false;
      };
    }

    // Poll for a short time for the safe wrapper to populate `raw` so
    // that we can render the real Toaster when available.
    const interval = window.setInterval(() => {
      const safeToastHolder = safeToast as unknown;
      const m =
        typeof safeToastHolder === "object" &&
        safeToastHolder !== null &&
        "raw" in (safeToastHolder as Record<string, unknown>)
          ? (safeToastHolder as Record<string, unknown>).raw
          : undefined;
      if (m) {
        const mRec = m as Record<string, unknown>;
        const { Toaster: ToasterComp, default: defaultExport } = mRec;
        const comp =
          ToasterComp ||
          (defaultExport &&
            (defaultExport as Record<string, unknown>)?.Toaster) ||
          (defaultExport as React.ComponentType);
        if (comp && mounted) {
          setToaster(() => comp as React.ComponentType<ToasterProps>);
        }
        clearInterval(interval);
      }
    }, 250);

    const timeout = window.setTimeout(() => clearInterval(interval), 5000);

    return () => {
      mounted = false;
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, []);

  if (!Toaster) {
    return null;
  }
  const C = Toaster;
  try {
    return (
      <C
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: "var(--bg-primary)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-primary)",
            borderRadius: "12px",
            padding: "16px",
            fontSize: "14px",
            maxWidth: "400px",
          },
          success: {
            iconTheme: {
              primary: "var(--text-success)",
              secondary: "var(--text-primary)",
            },
            style: {
              background: "var(--bg-primary)",
              color: "var(--text-primary)",
              border: "1px solid var(--text-success)",
            },
          },
          error: {
            iconTheme: {
              primary: "var(--text-danger)",
              secondary: "var(--text-primary)",
            },
            style: {
              background: "var(--bg-primary)",
              color: "var(--text-primary)",
              border: "1px solid var(--text-danger)",
            },
          },
        }}
      />
    );
  } catch (err) {
    logger.warn("ToasterClient: rendering Toaster threw, skipping", err);
    return null;
  }
}
