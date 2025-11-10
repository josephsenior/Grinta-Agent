import {
  Links,
  Meta,
  MetaFunction,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router-dom";
import "./tailwind.css";
import "./index.css";
import "./styles/forge-theme.css";
import React, { useEffect } from "react";
import ToasterClient from "./components/ToasterClient";
import { ThemeProvider } from "./context/theme-context";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider defaultTheme="dark">
      <Meta />
      <Links />
      {children}
      <ScrollRestoration />
      <Scripts />
      <ToasterClient />
    </ThemeProvider>
  );
}

export const meta: MetaFunction = () => [
  { title: "Forge Pro - Production-Grade AI Coding Assistant" },
  {
    name: "description",
    content:
      "Forge Pro: Built on open-source foundations, enhanced for production with enterprise-grade memory, world-class code quality (9.04/10), and performance optimizations.",
  },
  {
    property: "og:title",
    content: "Forge Pro - Production-Grade AI Coding Assistant",
  },
  {
    property: "og:description",
    content:
      "Enterprise-grade AI coding assistant with persistent memory, world-class code quality, and 64% faster performance.",
  },
  {
    property: "og:type",
    content: "website",
  },
  {
    name: "twitter:card",
    content: "summary_large_image",
  },
  {
    name: "twitter:title",
    content: "Forge Pro - Production-Grade AI Coding Assistant",
  },
  {
    name: "twitter:description",
    content:
      "Enterprise-grade AI coding assistant with persistent memory and world-class code quality.",
  },
];

// Hydration fallback for better UX during initial load
export function HydrateFallback() {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
        backgroundColor: "#0f1117",
        color: "#8b949e",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            width: "48px",
            height: "48px",
            border: "4px solid #21262d",
            borderTop: "4px solid #58a6ff",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
            margin: "0 auto 24px",
          }}
        />
        <div style={{ fontSize: "16px", fontWeight: 500 }}>
          Loading Forge Pro...
        </div>
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
  );
}

export default function App() {
  useEffect(() => {
    // Only run on client side to avoid hydration mismatch
    if (typeof window === "undefined") {
      return;
    }

    try {
      type MaybeImportMeta = { env?: Record<string, unknown> } | undefined;
      interface WindowWithFlags extends Window {
        __ALLOW_TOAST_IMPORTS__?: boolean;
      }

      const importMeta = import.meta as MaybeImportMeta;
      const win = window as unknown as WindowWithFlags;

      if (importMeta?.env && importMeta.env.DEV && win) {
        win.__ALLOW_TOAST_IMPORTS__ = true;
      }
    } catch (e) {
      // Swallow: best-effort feature flag set for dev only
      // eslint-disable-next-line no-console
      console.warn?.("root: allow toast imports feature flag set failed", e);
    }
  }, []);
  return <Outlet />;
}
