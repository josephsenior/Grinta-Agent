import React, { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { HydratedRouter } from "react-router/dom";
import { Provider } from "react-redux";
import { QueryClientProvider } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import store from "./store";
import { queryClient } from "./query-client-config";
import i18n from "./i18n";
import { logger } from "./utils/logger";

// Small, accessible fallback shown while route modules or client loaders run.
function HydrateFallback() {
  const { t } = useTranslation();
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
      <div style={{ marginTop: 12, color: "#222" }}>
        {t("MAIN$LOADING_APPLICATION", "Loading application…")}
      </div>
      <div style={{ marginTop: 6, color: "#666", fontSize: 13 }}>
        {t(
          "MAIN$PREPARING_UI",
          "Preparing UI — this usually only takes a moment.",
        )}
      </div>
    </div>
  );
}

// Minimal ErrorBoundary to avoid showing a blank page on hydration/runtime errors
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Log error for debugging
    logger.error("Hydration/runtime error:", error, info);
  }

  render() {
    const { hasError } = this.state;
    const { children } = this.props;

    if (hasError) {
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
          <h1 style={{ margin: 0 }}>
            {i18n.t("MAIN$SOMETHING_WENT_WRONG", "Something went wrong")}
          </h1>
          <p style={{ color: "#666" }}>
            {i18n.t(
              "MAIN$ERROR_STARTING_APP",
              "We encountered an error while starting the app. You can try reloading the page or open the console for details.",
            )}
          </p>
          <div style={{ marginTop: 12 }}>
            <button
              type="button"
              onClick={() => window.location.reload()}
              style={{ padding: "8px 12px", cursor: "pointer" }}
            >
              {i18n.t("MAIN$RELOAD", "Reload")}
            </button>
          </div>
        </div>
      );
    }

    return children as React.ReactElement;
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
