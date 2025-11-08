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

function isPlaywrightEnvironment(): boolean {
  try {
    return (
      typeof window !== "undefined" &&
      (window as Window & { __Forge_PLAYWRIGHT?: boolean }).__Forge_PLAYWRIGHT ===
        true
    );
  } catch {
    return false;
  }
}

function isProductionRuntime(): boolean {
  try {
    const isProdMeta =
      typeof import.meta !== "undefined" &&
      (import.meta as MaybeImportMeta).env &&
      (import.meta as MaybeImportMeta).env?.PROD === true;
    const isProdNode =
      typeof process !== "undefined" &&
      process.env &&
      process.env.NODE_ENV === "production";
    return isProdMeta || isProdNode;
  } catch {
    return true;
  }
}

function hasAllowImportFlag(): boolean {
  try {
    return (
      typeof window !== "undefined" &&
      (window as Window & { __ALLOW_TOAST_IMPORTS__?: boolean })
        .__ALLOW_TOAST_IMPORTS__ === true
    );
  } catch {
    return false;
  }
}

function isDevRuntime(): boolean {
  try {
    const isViteDev =
      typeof import.meta !== "undefined" &&
      (import.meta as MaybeImportMeta).env &&
      (import.meta as MaybeImportMeta).env?.DEV === true;
    const isNodeDev =
      typeof process !== "undefined" &&
      process.env &&
      process.env.NODE_ENV === "development";
    return Boolean(isViteDev || isNodeDev);
  } catch {
    return false;
  }
}

function flushQueuedCalls() {
  while (queue.length) {
    const queuedCall = queue.shift()!;
    try {
      const rt = realToast;
      if (!rt) {
        continue;
      }
      const fn = rt[queuedCall.method];
      if (typeof fn === "function") {
        (fn as (...args: unknown[]) => unknown)(...queuedCall.args);
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.warn("safe-hot-toast shim queued call failed", error);
    }
  }
}

function scheduleImport() {
  if (importScheduled) {
    return;
  }
  if (isPlaywrightEnvironment()) {
    return;
  }
  if (isProductionRuntime()) {
    return;
  }
  if (!hasAllowImportFlag()) {
    return;
  }
  importScheduled = true;
  // Emit diagnostic only when the allow flag is present (dev client)
  // eslint-disable-next-line no-console
  console.warn("safe-hot-toast: scheduling dynamic import of react-hot-toast");

  setTimeout(() => {
    if (!isDevRuntime()) {
      // eslint-disable-next-line no-console
      console.warn("safe-hot-toast: skipping dynamic import outside of dev");
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
        flushQueuedCalls();
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
