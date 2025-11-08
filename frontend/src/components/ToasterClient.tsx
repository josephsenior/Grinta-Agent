import React, { useEffect, useState } from "react";
import safeToast from "#/utils/safe-hot-toast";

// Client-only Toaster loader that does NOT import react-hot-toast
// directly. Instead we rely on the safe wrapper's `raw` field to
// expose the real library once it has loaded. This prevents importing
// the third-party bundle during hydration/SSR which previously caused
// an import-time TypeError in the goober runtime.
export default function ToasterClient(): React.ReactElement | null {
  const [Toaster, setToaster] = useState<React.ComponentType | null>(null);

  useEffect(() => {
    let mounted = true;

    // If the safe wrapper has already loaded the real library, use it.
    const holder = safeToast as unknown;
    const raw =
      typeof holder === "object" && holder !== null &&
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
        setToaster(() => comp as React.ComponentType);
      }
      return () => {
        mounted = false;
      };
    }

    // Poll for a short time for the safe wrapper to populate `raw` so
    // that we can render the real Toaster when available.
    const interval = window.setInterval(() => {
      const holder = safeToast as unknown;
      const m =
        typeof holder === "object" && holder !== null &&
        "raw" in (holder as Record<string, unknown>)
          ? (holder as Record<string, unknown>).raw
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
          setToaster(() => comp as React.ComponentType);
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
    return <C />;
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("ToasterClient: rendering Toaster threw, skipping", err);
    return null;
  }
}
