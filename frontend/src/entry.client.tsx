/* eslint-disable react/react-in-jsx-scope */
/**
 * By default, Remix will handle hydrating your app on the client for you.
 * You are free to delete this file if you'd like to, but if you ever want it revealed again, you can run `npx remix reveal` ✨
 * For more information, see https://remix.run/file-conventions/entry.client
 */

// Polyfill for React scheduler performance API
import React, { startTransition, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Provider } from "react-redux";
import posthog from "posthog-js";
import "./i18n";
// Import CSS files
import "./tailwind.css";
import "./index.css";
import "./styles/forge-theme.css";
import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./context/theme-context";
import store from "./store";
// ...existing imports
import Forge from "./api/forge";
import { displayErrorToast } from "./utils/custom-toast-handlers";
import { queryClient } from "./query-client-config";
import { performanceMonitor } from "./utils/performanceMonitor";

if (typeof performance === "undefined") {
  (globalThis as any).performance = {
    now: () => Date.now(),
  };
}
// Lazy load heavy dependencies
const fileIconsCSS = import("file-icons-js/css/style.css");
const fileIconsJS = import("file-icons-js");

// Lazy load heavy components
const ToasterClient = lazy(() => import("./components/ToasterClient"));

type WindowWithE2E = Window & {
  __Forge_PLAYWRIGHT?: boolean;
  __Forge_E2E_MARK?: ((name: string, meta?: unknown) => void) | undefined;
  __Forge_E2E_GET?: (() => unknown[]) | undefined;
  __Forge_E2E_APPLIED_RUNTIME_READY?: boolean;
};

const getWin = (): WindowWithE2E | undefined =>
  typeof window !== "undefined" ? (window as WindowWithE2E) : undefined;

// Synchronous dev-safety guard: when not running in production, replace
// common posthog methods with no-ops immediately at module load. This
// prevents any early or module-level posthog calls from generating
// network traffic or noisy logs before React effects have a chance to run.
if (process.env.NODE_ENV !== "production") {
  try {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const noop = (..._args: unknown[]) => undefined;
    /* posthog runtime augmentation for dev-only safety. We intentionally
     assign no-op implementations to methods that may not be in the
     type definitions at compile-time. Silence any TS complaints at the
     assignment site via eslint for clarity. */
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    posthog.capture = noop;
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    posthog.identify = noop;
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    posthog.opt_in_capturing = noop;
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    posthog.opt_out_capturing = noop;
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    posthog.has_opted_in_capturing = () => false;
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    posthog.has_opted_out_capturing = () => true;
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    posthog.captureException = noop;
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    posthog.reset = noop;
  } catch (e) {
    // Best-effort dev-only guard: log at debug level so issues are visible
    // during development without failing startup. Use String(e) because
    // safeMessage is defined later in this file.
    // eslint-disable-next-line no-console
    console.debug("Posthog dev-guard failed:", String(e));
  }
}

const safeMessage = (e: unknown): string => {
  try {
    if (e && typeof e === "object" && "message" in e) {
      const m = (e as unknown as Record<string, unknown>).message;
      if (typeof m === "string") {
        return m;
      }
    }
  } catch (_) {
    // eslint-disable-next-line no-console
    console.debug("safeMessage inner inspection failed");
  }
  try {
    return String(e);
  } catch (_) {
    // eslint-disable-next-line no-console
    console.debug("safeMessage stringify failed");
    return "";
  }
};

function PosthogInit() {
  const [posthogClientKey, setPosthogClientKey] = React.useState<string | null>(
    null,
  );

  React.useEffect(() => {
    (async () => {
      try {
        const config = await Forge.getConfig();
        setPosthogClientKey(config.POSTHOG_CLIENT_KEY);
      } catch (error) {
        displayErrorToast("Error fetching PostHog client key");
      }
    })();
  }, []);

  React.useEffect(() => {
    // Only initialize PostHog in production builds when a client key is provided.
    // This prevents noisy PostHog debug logs during local development.
    const shouldInitPosthog =
      process.env.NODE_ENV === "production" && Boolean(posthogClientKey);

    if (shouldInitPosthog && posthogClientKey) {
      try {
        posthog.init(posthogClientKey, {
          api_host: "https://us.i.posthog.com",
          person_profiles: "identified_only",
        });
      } catch (e) {
        // swallow initialization errors in client init path to prevent
        // spamming the console in dev-like environments where PostHog may
        // be misconfigured.
        // eslint-disable-next-line no-console
        console.warn("PostHog init failed:", e);
      }
    } else {
      // In non-production environments, replace commonly-used PostHog methods
      // with no-ops so that capture/identify calls across the app are silent
      // and do not produce network traffic or verbose logs. This intentionally
      // mirrors the guarded-init behavior without requiring edits at each
      // call-site.
      try {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const noop = (..._args: unknown[]) => undefined;
        // Common methods used in the codebase/tests
        // Silence type mismatches for test/dev runtime augmentation.
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore
        posthog.capture = noop;
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore
        posthog.identify = noop;
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore
        posthog.opt_in_capturing = noop;
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore
        posthog.opt_out_capturing = noop;
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore
        posthog.has_opted_in_capturing = () => false;
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore
        posthog.has_opted_out_capturing = () => true;
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore
        posthog.captureException = noop;
      } catch (e) {
        // Best-effort: if patching fails, do not crash the app in dev.
      }
    }
  }, [posthogClientKey]);

  return null;
}

async function prepareApp() {
  if (
    process.env.NODE_ENV === "development" &&
    import.meta.env.VITE_MOCK_API === "true"
  ) {
    const { worker } = await import("./mocks/browser");

    await worker.start({
      onUnhandledRequest: "bypass",
    });
  }
}

function EnsurePortalRoot() {
  React.useEffect(() => {
    const id = "modal-portal-exit";
    let node = document.getElementById(id);
    if (!node) {
      node = document.createElement("div");
      node.id = id;
      document.body.appendChild(node);
    }
  }, []);
  return null;
}

// Import skeleton loader
const SkeletonLoader = lazy(() => import("./components/SkeletonLoader"));

// Optimized loading component
function LoadingFallback() {
  return (
    <Suspense
      fallback={
        <div
          className="loading"
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            height: "100vh",
            fontSize: "18px",
            color: "#666",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                border: "4px solid #f3f3f3",
                borderTop: "4px solid #3498db",
                borderRadius: "50%",
                animation: "spin 1s linear infinite",
                margin: "0 auto 16px",
              }}
            />
            Loading Forge...
          </div>
          <style
            dangerouslySetInnerHTML={{
              __html: `
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `,
            }}
          />
        </div>
      }
    >
      <SkeletonLoader />
    </Suspense>
  );
}

prepareApp().then(async () => {
  // Initialize performance monitoring
  performanceMonitor.init();

  // Load CSS and JS asynchronously to avoid blocking
  await Promise.allSettled([
    fileIconsCSS.catch(() => {}), // Ignore errors for optional CSS
    fileIconsJS.catch(() => {}), // Ignore errors for optional JS
  ]);

  // ...existing startup logic
  // Remove any transient `data-demoway-document-id` that may have been
  // injected into the server HTML by external tooling (playback/recording
  // helpers). If left on the server DOM it will trigger a hydration
  // attribute mismatch because our client-side body does not render it.
  try {
    if (
      typeof document !== "undefined" &&
      document.body?.hasAttribute("data-demoway-document-id")
    ) {
      document.body.removeAttribute("data-demoway-document-id");
    }
  } catch (e) {
    // swallow - this is best-effort defensive code before hydration
  }

  startTransition(() => {
    let rootEl =
      typeof document !== "undefined" ? document.getElementById("root") : null;

    if (!rootEl) {
      // If the root element is missing, in development create a fallback
      // placeholder to avoid a completely blank page so developers can
      // see console diagnostics and iterate. In production we abort to
      // avoid masking SSR mismatch issues.
      if (process.env.NODE_ENV === "production") {
        // eslint-disable-next-line no-console
        console.error(
          "Cannot find #root element to hydrate into. Aborting hydration.",
        );
        return;
      }

      try {
        // eslint-disable-next-line no-console
        console.warn(
          "#root element missing — creating a dev-only fallback div#root. Check your index.html or any scripts that manipulate the DOM before hydration.",
        );
        const div = document.createElement("div");
        div.id = "root";
        // Apply minimal styles so the dev placeholder is visible when created.
        div.style.minHeight = "100vh";
        document.body.insertBefore(div, document.body.firstChild);
        rootEl = div;
      } catch (e) {
        // If we cannot create a fallback, abort.
        // eslint-disable-next-line no-console
        console.error(
          "Failed to create fallback #root element:",
          safeMessage(e),
        );
        return;
      }
    }

    // Dynamically import RootLayout to avoid SSR issues
    import("./routes/root-layout").then(({ default: RootLayout }) => {
      // Create router with lazy-loaded routes for better code splitting
      const router = createBrowserRouter(
        [
          {
            path: "/",
            Component: RootLayout, // Use Component instead of element to defer instantiation
            HydrateFallback: () => <div className="min-h-screen bg-black" />,
            children: [
              {
                index: true,
                lazy: () =>
                  import("./routes/home").then((m) => ({
                    Component: m.default,
                  })),
              },
              {
                path: "accept-tos",
                lazy: () =>
                  import("./routes/accept-tos").then((m) => ({
                    Component: m.default,
                  })),
              },
              {
                path: "about",
                lazy: () =>
                  import("./routes/about").then((m) => ({
                    Component: m.default,
                  })),
              },
              {
                path: "contact",
                lazy: () =>
                  import("./routes/contact").then((m) => ({
                    Component: m.default,
                  })),
              },
              {
                path: "terms",
                lazy: () =>
                  import("./routes/terms").then((m) => ({
                    Component: m.default,
                  })),
              },
              {
                path: "privacy",
                lazy: () =>
                  import("./routes/privacy").then((m) => ({
                    Component: m.default,
                  })),
              },
              {
                path: "settings",
                lazy: () =>
                  import("./routes/settings").then((m) => ({
                    Component: m.default,
                  })),
                children: [
                  {
                    index: true,
                    lazy: () =>
                      import("./routes/llm-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "mcp",
                    lazy: () =>
                      import("./routes/mcp-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "user",
                    lazy: () =>
                      import("./routes/user-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "integrations",
                    lazy: () =>
                      import("./routes/git-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "databases",
                    lazy: () =>
                      import("./routes/database-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "memory",
                    lazy: () =>
                      import("./routes/memory-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "analytics",
                    lazy: () =>
                      import("./routes/analytics-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "prompts",
                    lazy: () =>
                      import("./routes/prompts-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "snippets",
                    lazy: () =>
                      import("./routes/snippets-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "slack",
                    lazy: () =>
                      import("./routes/slack-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "backup",
                    lazy: () =>
                      import("./routes/backup-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "app",
                    lazy: () =>
                      import("./routes/app-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "billing",
                    lazy: () =>
                      import("./routes/billing").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "secrets",
                    lazy: () =>
                      import("./routes/secrets-settings").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "api-keys",
                    lazy: () =>
                      import("./routes/api-keys").then((m) => ({
                        Component: m.default,
                      })),
                  },
                ],
              },
              {
                path: "database-browser",
                lazy: () =>
                  import("./routes/database-browser").then((m) => ({
                    Component: m.default,
                  })),
              },
              {
                path: "conversation",
                lazy: () =>
                  import("./routes/conversation-redirect").then((m) => ({
                    Component: m.default,
                  })),
              },
              {
                path: "conversations",
                lazy: () =>
                  import("./routes/conversations-list").then((m) => ({
                    Component: m.default,
                  })),
              },
              {
                path: "conversations/:conversationId",
                lazy: () =>
                  import("./routes/conversation").then((m) => ({
                    Component: m.default,
                  })),
                children: [
                  {
                    index: true,
                    lazy: () =>
                      import("./routes/workspace-tab").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "browser",
                    lazy: () =>
                      import("./routes/browser-tab").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "jupyter",
                    lazy: () =>
                      import("./routes/jupyter-tab").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "served",
                    lazy: () =>
                      import("./routes/served-tab").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "terminal",
                    lazy: () =>
                      import("./routes/terminal-tab").then((m) => ({
                        Component: m.default,
                      })),
                  },
                  {
                    path: "vscode",
                    lazy: () =>
                      import("./routes/vscode-tab").then((m) => ({
                        Component: m.default,
                      })),
                  },
                ],
              },
              {
                path: "microagent-management",
                lazy: () =>
                  import("./routes/microagent-management").then((m) => ({
                    Component: m.default,
                  })),
              },
            ],
          },
        ],
        {
          future: {
            v7_startTransition: true,
            v7_relativeSplatPath: true,
            v7_fetcherPersist: true,
            v7_normalizeFormMethod: true,
            v7_partialHydration: true,
            v7_skipActionErrorRevalidation: true,
          },
        },
      );

      createRoot(rootEl).render(
        <ThemeProvider defaultTheme="dark">
          <Provider store={store}>
            <QueryClientProvider client={queryClient}>
              <RouterProvider router={router} />
              <ToasterClient />
              <PosthogInit />
              <EnsurePortalRoot />
            </QueryClientProvider>
          </Provider>
        </ThemeProvider>,
      );
    });
  });
});

// Test-only: expose a small E2E hook to allow Playwright runs to mark the
// runtime as ready in a narrowly-scoped way. This helps tests that need the
// UI to render file lists without performing a broad sweep of curAgentState
// usages. Only activate when the Playwright init script sets the global
// test flag `window.__Forge_PLAYWRIGHT === true` so production behavior
// is unchanged.
try {
  const w = getWin();
  if (w && w.__Forge_PLAYWRIGHT === true) {
    const orig = w.__Forge_E2E_MARK;
    w.__Forge_E2E_MARK = function e2eMark(name: string, meta?: unknown) {
      try {
        // preserve original logging behavior if present
        if (typeof orig === "function") {
          try {
            orig(name, meta);
          } catch (e) {
            // swallow - preserve original behavior in tests
          }
        }

        if (name === "runtime-ready") {
          // dispatch a runtime-ready state into the store so components that
          // gate rendering on agent state become available for tests. This
          // is intentionally narrow: only sets RUNNING in Playwright runs.
          try {
            // Import dynamically inside an async IIFE to allow top-level await
            (async () => {
              const modAgentState = await import("#/types/agent-state");
              const modAgentSlice = await import("#/state/agent-slice");
              // test-only dynamic import types are loose
              store.dispatch(
                modAgentSlice.setCurrentAgentState(
                  modAgentState.AgentState.RUNNING,
                ),
              );
            })().catch((e) => {
              // swallow - this is strictly diagnostic/test-only
              // eslint-disable-next-line no-console
              console.warn(
                "E2E_MARK runtime-ready dispatch failed",
                safeMessage(e),
              );
            });
          } catch (e) {
            // swallow - this is strictly diagnostic/test-only
            // eslint-disable-next-line no-console
            console.warn(
              "E2E_MARK runtime-ready dispatch failed",
              safeMessage(e),
            );
          } finally {
            // Test-only diagnostic: mark that the runtime-ready dispatch was attempted
            try {
              if (w) {
                w.__Forge_E2E_APPLIED_RUNTIME_READY = true;
              }
            } catch (e) {
              // swallow
            }
          }
        }
      } catch (e) {
        // swallow
      }
    };
  }
} catch (e) {
  // ignore any errors in test-only wiring
}

// Test-only startup race mitigation: if the Playwright init script recorded
// a 'runtime-ready' mark before the app installed the override, detect that
// recorded mark now and apply the same runtime-ready dispatch immediately.
try {
  const w = getWin();
  if (w && w.__Forge_PLAYWRIGHT === true) {
    try {
      const getMarks = w.__Forge_E2E_GET;
      if (typeof getMarks === "function") {
        try {
          const marks = getMarks();
          if (
            Array.isArray(marks) &&
            marks.some((m) => {
              if (!m || typeof m !== "object") {
                return false;
              }
              const ev = (m as Record<string, unknown>).event;
              return ev === "runtime-ready";
            })
          ) {
            // Same dispatch path as above — guarded to Playwright runs only.
            try {
              (async () => {
                const modAgentState = await import("#/types/agent-state");
                const modAgentSlice = await import("#/state/agent-slice");
                // test-only dynamic import types are loose
                store.dispatch(
                  modAgentSlice.setCurrentAgentState(
                    modAgentState.AgentState.RUNNING,
                  ),
                );
                // mark applied flag for tests
                try {
                  if (w) {
                    w.__Forge_E2E_APPLIED_RUNTIME_READY = true;
                  }
                } catch (e) {
                  /* ignore */
                }
                // eslint-disable-next-line no-console
                console.log(
                  "E2E: applied runtime-ready dispatch from recorded marks",
                );
              })().catch((e) => {
                // eslint-disable-next-line no-console
                console.warn(
                  "E2E: failed to apply recorded runtime-ready dispatch",
                  safeMessage(e),
                );
              });
            } catch (e) {
              // eslint-disable-next-line no-console
              console.warn(
                "E2E: failed to apply recorded runtime-ready dispatch",
                safeMessage(e),
              );
            }
          }
        } catch (e) {
          // swallow mark inspection errors
        }
      }
    } catch (e) {
      // swallow
    }
  }
} catch (e) {
  // ignore any errors in this best-effort diagnostic wiring
}
