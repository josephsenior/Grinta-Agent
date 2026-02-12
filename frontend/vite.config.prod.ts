/// <reference types="vitest" />
/// <reference types="vite-plugin-svgr/client" />
import { defineConfig, loadEnv } from "vite";
import type { ViteDevServer } from "vite";
import type { IncomingMessage, ServerResponse } from "http";
import path from "path";
import viteTsconfigPaths from "vite-tsconfig-paths";
import svgr from "vite-plugin-svgr";
// import reactRouterPlugin from "./scripts/react-router-plugin-wrapper.mjs";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const {
    VITE_BACKEND_HOST = "127.0.0.1:3000",
    VITE_USE_TLS = "false",
    VITE_FRONTEND_PORT = "3001",
    VITE_INSECURE_SKIP_VERIFY = "false",
  } = loadEnv(mode, process.cwd());

  const USE_TLS = VITE_USE_TLS === "true";
  const INSECURE_SKIP_VERIFY = VITE_INSECURE_SKIP_VERIFY === "true";
  const PROTOCOL = USE_TLS ? "https" : "http";
  const WS_PROTOCOL = USE_TLS ? "wss" : "ws";

  const API_URL = `${PROTOCOL}://${VITE_BACKEND_HOST}/`;
  const WS_URL = `${WS_PROTOCOL}://${VITE_BACKEND_HOST}/`;
  const FE_PORT = Number.parseInt(VITE_FRONTEND_PORT, 10);

  return {
    build: {
      // Production optimizations
      sourcemap: 'hidden',  // Generate hidden source maps for Sentry debugging
      target: 'es2020',  // Modern target for smaller bundles
      minify: 'esbuild',
      cssCodeSplit: true,
      reportCompressedSize: false,
      rollupOptions: {
        output: {
          manualChunks: (id) => {
            // Ultra-aggressive chunking for maximum performance
            if (id.includes('node_modules')) {
              if (id.includes('react') || id.includes('react-dom')) {
                return 'react-core';
              }
              if (id.includes('@heroui') || id.includes('@radix-ui')) {
                return 'ui-core';
              }
              if (id.includes('@monaco-editor')) {
                return 'editor';
              }
              if (id.includes('xterm')) {
                return 'terminal';
              }
              if (id.includes('react-icons') || id.includes('lucide')) {
                return 'icons';
              }
              if (id.includes('mermaid') || id.includes('cytoscape') || id.includes('dagre')) {
                return 'diagrams';
              }
              if (id.includes('katex')) {
                return 'heavy-math';
              }
              if (id.includes('socket.io')) {
                return 'websocket';
              }
              if (id.includes('axios') || id.includes('fetch')) {
                return 'http';
              }
              if (id.includes('i18next')) {
                return 'i18n';
              }
              return 'vendor';
            }
            // Route-based splitting
            if (id.includes('src/routes/home')) return 'route-home';
            if (id.includes('src/routes/conversation')) return 'route-conversation';
            if (id.includes('src/routes/settings')) return 'route-settings';
            if (id.includes('src/components/features/chat')) return 'chat';
            if (id.includes('src/components/features/orchestration')) return 'orchestration';
            if (id.includes('src/components/features/browser')) return 'browser';
          },
          chunkFileNames: 'assets/[name]-[hash].js',
          entryFileNames: 'assets/[name]-[hash].js',
          assetFileNames: 'assets/[name]-[hash].[ext]',
        },
      },
      chunkSizeWarningLimit: 500, // Stricter limit
    },
    resolve: {
      alias: {
        "#": path.resolve(process.cwd(), "src"),
        "#/": path.resolve(process.cwd(), "src") + "/",
      },
      // CRITICAL: Deduplicate React to prevent "Invalid hook call" errors
      dedupe: ["react", "react-dom"],
    },
    plugins: [
      // reactRouterPlugin,
      viteTsconfigPaths(),
      svgr(),
      tailwindcss(),
    ].flat().filter(Boolean),
    optimizeDeps: {
      include: [
        "react-redux",
        "@tanstack/react-query",
        "react-hot-toast",
        "@reduxjs/toolkit",
        "axios",
        "clsx",
        "tailwind-merge",
      ],
      force: true,
    },
    server: {
      port: FE_PORT,
      host: true,
      allowedHosts: true,
      proxy: {
        "/api": {
          target: API_URL,
          changeOrigin: true,
          secure: !INSECURE_SKIP_VERIFY,
        },
        "/ws": {
          target: WS_URL,
          ws: true,
          changeOrigin: true,
          secure: !INSECURE_SKIP_VERIFY,
        },
        "/socket.io": {
          target: WS_URL,
          ws: true,
          changeOrigin: true,
          secure: !INSECURE_SKIP_VERIFY,
        },
      },
    },
    clearScreen: false,
  };
});
