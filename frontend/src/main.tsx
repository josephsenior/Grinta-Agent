import React, { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { HydratedRouter } from "react-router/dom";
import { Provider } from "react-redux";
import { QueryClientProvider } from "@tanstack/react-query";
import store from "./store";
import { queryClient } from "./query-client-config";
import "./i18n";

// Small, accessible fallback shown while route modules or client loaders run.
function HydrateFallback() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className="loading"
      style={{ padding: "24px", textAlign: "center" }}
    >
      <svg
        width="48"
        height="48"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke="#888"
          strokeWidth="2"
          opacity="0.25"
        />
        <path d="M22 12A10 10 0 0 1 12 22" stroke="#111" strokeWidth="2">
          <animateTransform
            attributeName="transform"
            type="rotate"
            from="0 12 12"
            to="360 12 12"
            dur="1s"
            repeatCount="indefinite"
          />
        </path>
      </svg>
      <div style={{ marginTop: 12, color: "#222" }}>Loading application…</div>
      <div style={{ marginTop: 6, color: "#666", fontSize: 13 }}>
        Preparing UI — this usually only takes a moment.
      </div>
    </div>
  );
}

// Minimal ErrorBoundary to avoid showing a blank page on hydration/runtime errors
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error?: Error | null }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: any) {
    // Keep console output readable during development
    // eslint-disable-next-line no-console
    console.error("Hydration/runtime error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
            textAlign: "center",
          }}
        >
          <h1 style={{ margin: 0 }}>Something went wrong</h1>
          <p style={{ color: "#666" }}>
            We encountered an error while starting the app. You can try
            reloading the page or open the console for details.
          </p>
          <div style={{ marginTop: 12 }}>
            <button
              onClick={() => window.location.reload()}
              style={{ padding: "8px 12px", cursor: "pointer" }}
            >
              Reload
            </button>
          </div>
        </div>
      );
    }

    return this.props.children as React.ReactElement;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <Provider store={store}>
        <QueryClientProvider client={queryClient}>
          <Suspense fallback={<HydrateFallback />}>
            <HydratedRouter />
          </Suspense>
        </QueryClientProvider>
      </Provider>
    </ErrorBoundary>
  </StrictMode>,
);
