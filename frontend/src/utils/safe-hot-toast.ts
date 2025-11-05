import React from "react";
import type { ToastOptions } from "react-hot-toast";
// Minimal normalize helper (avoid importing other utils to keep shim self-contained)
function normalizeToastMessage(input: unknown): string {
  if (input == null) {
    return "";
  }
  if (typeof input === "string") {
    return input;
  }
  try {
    if (input && typeof input === "object" && "message" in input) {
      const rec = input as Record<string, unknown>;
      if (typeof rec.message === "string") return rec.message as string;
    }
  } catch (e) {
    // ignore parse errors when inspecting message property
    // eslint-disable-next-line no-console
    console.warn("safe-hot-toast: normalizeToastMessage parse error", e);
  }
  try {
    return String(input);
  } catch (e) {
    // Fallback to empty string if toString fails
    // eslint-disable-next-line no-console
    console.warn("safe-hot-toast: normalizeToastMessage stringify failed", e);
    return "";
  }
}

type QueuedCall = {
  method: "show" | "success" | "error" | "dismiss";
  args: unknown[];
};
const queue: QueuedCall[] = [];
type RealToastLike = {
  show?: (
    msg: string | React.ReactElement | (() => React.ReactElement),
    opts?: ToastOptions,
  ) => unknown;
  success?: (msg: string, opts?: ToastOptions) => unknown;
  error?: (msg: string, opts?: ToastOptions) => unknown;
  dismiss?: (id?: string | number) => unknown;
};

let realToast: RealToastLike | null = null;
let importScheduled = false;
let isNoopFallback = true;
// Build-time constant that Vite will replace. If true, produce a strict
// no-op `safe` object below so the production bundle contains no import()
// code paths for react-hot-toast.
type MaybeImportMeta = { env?: Record<string, unknown> };
const IS_PROD_BUILD =
  typeof import.meta !== "undefined" &&
  (import.meta as MaybeImportMeta).env &&
  (import.meta as MaybeImportMeta).env?.PROD === true;

function scheduleImport() {
  if (importScheduled) {
    return;
  }
  // In Playwright E2E runs we don't want to attempt dynamic imports that
  // can be flaky in the headful test environment. Respect the test flag
  // that tests set on window so we keep a stable noop fallback in tests.
  try {
    if (
      typeof window !== "undefined" &&
      (window as Window & { __OPENHANDS_PLAYWRIGHT?: boolean })
        .__OPENHANDS_PLAYWRIGHT === true
    ) {
      // Do not schedule or attempt dynamic imports in Playwright runs.
      return;
    }
  } catch (e) {
    // ignore
  }
  // Bail immediately in production builds — do not schedule or import.
  try {
    const isProd =
      (typeof import.meta !== "undefined" &&
        (import.meta as MaybeImportMeta).env &&
        (import.meta as MaybeImportMeta).env?.PROD === true) ||
      (typeof process !== "undefined" &&
        process.env &&
        process.env.NODE_ENV === "production");
    if (isProd) {
      return;
    }
  } catch (_) {
    // If we can't evaluate env flags, be conservative and bail.
    return;
  }

  // Quick allow-flag check: if the client root didn't opt-in, exit silently.
  try {
    const allowFlag =
      typeof window !== "undefined" &&
      (window as Window & { __ALLOW_TOAST_IMPORTS__?: boolean })
        .__ALLOW_TOAST_IMPORTS__ === true;
    if (!allowFlag) {
      return;
    }
  } catch (_) {
    return;
  }
  importScheduled = true;
  // Emit diagnostic only when the allow flag is present (dev client)
  // eslint-disable-next-line no-console
  console.warn("safe-hot-toast: scheduling dynamic import of react-hot-toast");

  setTimeout(() => {
    // Only attempt dynamic import in development builds. In production
    // we keep the noop fallback active to avoid import-time crashes.
    try {
      const isViteDev =
        typeof import.meta !== "undefined" &&
        (import.meta as MaybeImportMeta).env &&
        (import.meta as MaybeImportMeta).env?.DEV === true;
      const isNodeDev =
        typeof process !== "undefined" &&
        process.env &&
        process.env.NODE_ENV === "development";
      if (!isViteDev && !isNodeDev) {
        // eslint-disable-next-line no-console
        console.warn("safe-hot-toast: skipping dynamic import outside of dev");
        importScheduled = false;
        return;
      }
    } catch (_) {
      importScheduled = false;
      return;
    }

    // eslint-disable-next-line no-console
    console.warn("safe-hot-toast: starting dynamic import");
    import("react-hot-toast")
      .then((m) => {
        const imported = m as Record<string, unknown>;
        realToast = (imported.default ?? imported) as RealToastLike;
        isNoopFallback = false;
        while (queue.length) {
          const c = queue.shift()!;
          try {
            const rt = realToast as RealToastLike | null;
            if (rt) {
              const fn = rt[c.method];
              if (typeof fn === "function") {
                // All queued calls were originally pushed with known argument shapes
                (fn as (...args: unknown[]) => unknown)(...c.args);
              }
            }
          } catch (e) {
            // ignore
            // eslint-disable-next-line no-console
            console.warn("safe-hot-toast shim queued call failed", e);
          }
        }
      })
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.warn("safe-hot-toast shim: dynamic import failed", err);
      });
  }, 0);
}

type SafeToast = {
  raw?: unknown;
  show: (msg: unknown, opts?: ToastOptions) => unknown;
  success: (msg: unknown, opts?: ToastOptions) => unknown;
  error: (msg: unknown, opts?: ToastOptions) => unknown;
  dismiss: (id?: string | number) => unknown;
};

let safeInternal: SafeToast;

if (IS_PROD_BUILD) {
  // Strict no-op in production builds.
  safeInternal = Object.freeze({
    raw: undefined,
    show: () => undefined,
    success: () => undefined,
    error: () => undefined,
    dismiss: () => undefined,
  });
} else {
  safeInternal = {
    raw: undefined as unknown,
    show: (msg: unknown, opts?: ToastOptions) => {
      if (isNoopFallback) {
        scheduleImport();
        queue.push({ method: "show", args: [msg, opts] });
        return undefined;
      }
      try {
        if (realToast) {
          // Normalize the message into the exact union accepted by react-hot-toast
          // (string | ReactElement | () => ReactElement) so we avoid `as any` calls.
          let resolvedMsg:
            | string
            | React.ReactElement
            | (() => React.ReactElement);
          if (typeof msg === "function") {
            // Caller provided a function that returns a React element
            resolvedMsg = msg as () => React.ReactElement;
          } else if (React.isValidElement(msg)) {
            resolvedMsg = msg;
          } else if (typeof msg === "string") {
            resolvedMsg = msg;
          } else {
            resolvedMsg = normalizeToastMessage(msg);
          }
          return realToast.show?.(resolvedMsg, opts);
        }
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("safe-hot-toast shim: show failed", err);
        return undefined;
      }
    },
    success: (msg: unknown, opts?: ToastOptions) => {
      if (isNoopFallback) {
        scheduleImport();
        queue.push({ method: "success", args: [msg, opts] });
        return undefined;
      }
      try {
        if (realToast && typeof realToast.success === "function") {
          return realToast.success(
            typeof msg === "string" ? msg : normalizeToastMessage(msg),
            opts,
          );
        }
        return undefined;
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("safe-hot-toast shim: success failed", err);
        return undefined;
      }
    },
    error: (msg: unknown, opts?: ToastOptions) => {
      if (isNoopFallback) {
        scheduleImport();
        queue.push({ method: "error", args: [msg, opts] });
        return undefined;
      }
      try {
        if (realToast && typeof realToast.error === "function") {
          return realToast.error(
            typeof msg === "string" ? msg : normalizeToastMessage(msg),
            opts,
          );
        }
        return undefined;
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("safe-hot-toast shim: error failed", err);
        return undefined;
      }
    },
    dismiss: (id?: string | number) => {
      if (isNoopFallback) {
        scheduleImport();
        queue.push({ method: "dismiss", args: [id] });
        return undefined;
      }
      try {
        if (realToast && typeof realToast.dismiss === "function") {
          return realToast.dismiss(id);
        }
        return undefined;
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("safe-hot-toast shim: dismiss failed", err);
        return undefined;
      }
    },
  };
}

// Export a const to satisfy import/no-mutable-exports and make the
// exported symbol immutable from consumers' perspective.
const safe: SafeToast = safeInternal;
export default safe;
