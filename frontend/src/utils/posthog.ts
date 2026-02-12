/**
 * PostHog analytics wrapper — no-ops when PostHog is not configured.
 *
 * Usage: import posthog from "#/utils/posthog" (instead of "posthog-js")
 *
 * PostHog is loaded only when VITE_POSTHOG_ENABLED=true. Otherwise every
 * method call is a silent no-op, and the ~100KB PostHog bundle is excluded
 * from the build via tree-shaking.
 */

type PostHogLike = {
  capture: (event: string, properties?: Record<string, unknown>) => void;
  identify: (distinctId: string, properties?: Record<string, unknown>) => void;
  captureException: (error: unknown, properties?: Record<string, unknown>) => void;
  opt_in_capturing: () => void;
  opt_out_capturing: () => void;
  has_opted_in_capturing: () => boolean;
  has_opted_out_capturing: () => boolean;
  reset: () => void;
};

const noop = () => {};

const noopFalse = () => false;

const noopPostHog: PostHogLike = {
  capture: noop,
  identify: noop,
  captureException: noop,
  opt_in_capturing: noop,
  opt_out_capturing: noop,
  has_opted_in_capturing: noopFalse,
  has_opted_out_capturing: noopFalse,
  reset: noop,
};

function isPostHogEnabled(): boolean {
  try {
    const flag = import.meta.env.VITE_POSTHOG_ENABLED;
    return typeof flag === "string" && flag.toLowerCase() === "true";
  } catch {
    return false;
  }
}

let _posthog: PostHogLike = noopPostHog;

if (isPostHogEnabled()) {
  // Dynamic import: only loads the PostHog bundle when enabled
  import("posthog-js")
    .then((mod) => {
      _posthog = mod.default;
    })
    .catch(() => {
      // PostHog SDK not installed or failed to load — stay with no-op
    });
}

export default new Proxy(noopPostHog, {
  get(_target, prop: string) {
    return (...args: unknown[]) => {
      const fn = (_posthog as Record<string, unknown>)[prop];
      if (typeof fn === "function") {
        return fn.apply(_posthog, args);
      }
    };
  },
});
