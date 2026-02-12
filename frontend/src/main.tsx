/* eslint-disable react/react-in-jsx-scope */
// Polyfill for React scheduler performance API
import React, { startTransition, Suspense, lazy, useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Provider } from "react-redux";
import "./i18n";

// Import CSS files
import "./tailwind.css";
import "./index.css";
import "./styles/forge-theme.css";

import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./context/theme-context";
import store from "./store";
import { queryClient } from "./query-client-config";
import { performanceMonitor } from "./utils/performanceMonitor";

// --- GLOBAL POLYFILLS & SETUP ---

if (typeof performance === "undefined") {
  (globalThis as { performance?: { now: () => number } }).performance = {
    now: () => Date.now(),
  };
}

// Lazy load heavy dependencies
const fileIconsCSS = import("file-icons-js/css/style.css");
const fileIconsJS = import("file-icons-js");

// Lazy load heavy components
const ToasterClient = lazy(() => import("./components/toaster-client"));

// --- SPLASH SCREEN COMPONENT ---

const SplashScreen = () => {
  return (
    <div className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-[#0d0d0d] font-mono text-xs text-[#a3a3a3]">
      <div className="flex flex-col items-center gap-6">
        {/* Animated Logo */}
        <div className="relative h-16 w-16">
          <div className="absolute inset-0 animate-ping rounded-full bg-[#3b82f6] opacity-20"></div>
          <div className="absolute inset-2 animate-[spin_3s_linear_infinite] rounded-lg border-2 border-[#3b82f6] opacity-60"></div>
          <div className="absolute inset-4 rounded bg-[#3b82f6]"></div>
        </div>

        {/* Loading Text with typing effect */}
        <div className="flex flex-col items-center gap-1">
          <span className="text-sm font-semibold text-white tracking-widest uppercase">Forge IDE</span>
          <span className="animate-pulse text-[#525252]">Initializing runtime environment...</span>
        </div>

        {/* Progress Bar */}
        <div className="h-1 w-48 overflow-hidden rounded-full bg-[#262626]">
          <div className="h-full w-full animate-[loading_1.5s_ease-in-out_infinite] bg-[#3b82f6]"></div>
        </div>
      </div>
      
      {/* Footer Version */}
      <div className="absolute bottom-8 text-[#404040]">v0.55.0</div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes loading {
          0% { transform: translateX(-100%); }
          50% { transform: translateX(0%); }
          100% { transform: translateX(100%); }
        }
      `}} />
    </div>
  );
};

// --- APP PREPARATION ---

async function prepareApp() {
  // Initialize performance monitoring
  performanceMonitor.init();

  // Load CSS and JS asynchronously
  await Promise.allSettled([
    fileIconsCSS.catch(() => {}), // Ignore errors for optional CSS
    fileIconsJS.catch(() => {}), // Ignore errors for optional JS
  ]);

  // Mock API for dev/test
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

// --- E2E PLAYWRIGHT HOOKS (Preserved) ---
// Keep all the test hook logic intact
type WindowWithE2E = Window & {
    __Forge_PLAYWRIGHT?: boolean;
    __Forge_E2E_MARK?: ((name: string, meta?: unknown) => void) | undefined;
    __Forge_E2E_GET?: (() => unknown[]) | undefined;
    __Forge_E2E_APPLIED_RUNTIME_READY?: boolean;
};
  
const getWin = (): WindowWithE2E | undefined =>
    typeof window !== "undefined" ? (window as WindowWithE2E) : undefined;

const safeMessage = (e: unknown): string => {
    try {
        return e instanceof Error ? e.message : String(e);
    } catch {
        return "";
    }
};

const setupE2EHooks = () => {
    try {
        const w = getWin();
        if (w && w.__Forge_PLAYWRIGHT === true) {
            const orig = w.__Forge_E2E_MARK;
            w.__Forge_E2E_MARK = function e2eMark(name: string, meta?: unknown) {
              try {
                if (typeof orig === "function") orig(name, meta);
                if (name === "runtime-ready") {
                    (async () => {
                        const modAgentState = await import("#/types/agent-state");
                        const modAgentSlice = await import("#/state/agent-slice");
                        store.dispatch(modAgentSlice.setCurrentAgentState(modAgentState.AgentState.RUNNING));
                    })().catch(() => {});
                    try { if (w) w.__Forge_E2E_APPLIED_RUNTIME_READY = true; } catch {}
                }
              } catch {}
            };
        }
    } catch {}
};

// Run E2E setup immediately
setupE2EHooks();


// --- MOUNT REACT APP ---

prepareApp().then(() => {
    
    // Clean up server-side artifacts
    try {
        if (typeof document !== "undefined" && document.body?.hasAttribute("data-demoway-document-id")) {
            document.body.removeAttribute("data-demoway-document-id");
        }
    } catch {}

    startTransition(() => {
        let rootEl = document.getElementById("root");

        // Fallback for missing root (mostly for dev)
        if (!rootEl) {
            if (process.env.NODE_ENV === "production") {
                console.error("Cannot find #root element. Aborting.");
                return;
            }
            const div = document.createElement("div");
            div.id = "root";
            div.style.minHeight = "100vh";
            document.body.insertBefore(div, document.body.firstChild);
            rootEl = div;
        }

        // Import RootLayout lazily
        import("./routes/root-layout").then(({ default: RootLayout }) => {
            const router = createBrowserRouter(
                [
                    {
                        path: "/",
                        Component: RootLayout,
                        HydrateFallback: SplashScreen, // Use our sleek splash screen as the fallback
                        children: [
                            {
                                index: true,
                                lazy: () => import("./routes/index-redirect").then((m) => ({ Component: m.default })),
                            },
                            {
                                path: "search",
                                lazy: () => import("./routes/search").then((m) => ({ Component: m.default })),
                            },
                            {
                                path: "settings",
                                lazy: () => import("./routes/settings").then((m) => ({ Component: m.default })),
                                children: [
                                    { index: true, lazy: () => import("./routes/llm-settings").then((m) => ({ Component: m.default })) },
                                    { path: "llm", lazy: () => import("./routes/llm-settings").then((m) => ({ Component: m.default })) },
                                    { path: "app", lazy: () => import("./routes/app-settings").then((m) => ({ Component: m.default })) },
                                    { path: "mcp", lazy: () => import("./routes/mcp-settings").then((m) => ({ Component: m.default })) },
                                ],
                            },
                            {
                                path: "conversation",
                                lazy: () => import("./routes/conversation-redirect").then((m) => ({ Component: m.default })),
                            },
                            {
                                path: "conversations",
                                lazy: () => import("./routes/index-redirect").then((m) => ({ Component: m.default })),
                            },
                            {
                                path: "conversations/:conversationId",
                                lazy: () => import("./routes/conversation").then((m) => ({ Component: m.default })),
                                children: [
                                    { index: true, lazy: () => import("./routes/workspace-tab").then((m) => ({ Component: m.default })) },
                                    { path: "terminal", lazy: () => import("./routes/terminal-tab").then((m) => ({ Component: m.default })) },
                                    { path: "browser", lazy: () => import("./routes/browser-tab").then((m) => ({ Component: m.default })) },
                                ],
                            },
                            {
                                path: "*",
                                lazy: () => import("./routes/404").then((m) => ({ Component: m.default })),
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

            createRoot(rootEl!).render(
                <ThemeProvider defaultTheme="dark">
                    <Provider store={store}>
                        <QueryClientProvider client={queryClient}>
                            <RouterProvider router={router} />
                            <ToasterClient />
                            <EnsurePortalRoot />
                        </QueryClientProvider>
                    </Provider>
                </ThemeProvider>
            );
            
            // Cleanup performance monitoring on page unload
            window.addEventListener('beforeunload', () => {
                performanceMonitor.disconnect();
            });
        });
    });
});
