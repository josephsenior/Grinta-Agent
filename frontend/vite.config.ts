/// <reference types="vitest" />
/// <reference types="vite-plugin-svgr/client" />
import { defineConfig, loadEnv } from "vite";
import path from "path";
import viteTsconfigPaths from "vite-tsconfig-paths";
import svgr from "vite-plugin-svgr";
import tailwindcss from "@tailwindcss/vite";
import fixManifestPlugin from "./vite-plugin-fix-manifest.js";
import reactRouterPlugin from "./scripts/react-router-plugin-wrapper.mjs";

export default defineConfig(({ mode }) => {
  const envVars = loadEnv(mode, process.cwd());
  // Disable React Router plugin for pure SPA mode (no SSR)
  const PURE_SPA = true;

  const {
    VITE_BACKEND_HOST = "localhost:3000",
    VITE_USE_TLS = "false",
    VITE_FRONTEND_PORT = "3001",
    VITE_INSECURE_SKIP_VERIFY = "false",
  } = envVars;

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
      sourcemap: false,
      target: "es2015",
      minify: "esbuild",
      cssCodeSplit: true,
      reportCompressedSize: false,
      rollupOptions: {
        external: [],
        output: {
          format: 'es', // Force ES modules, not CommonJS
          globals: {},
          manualChunks: (id) => {
            // Exclude scheduler from vendor to avoid CommonJS wrapper issues
            if (id.includes('scheduler')) {
              return 'scheduler';
            }
            // Aggressive chunking for performance
            if (id.includes("node_modules")) {
              // Core React (load first, smallest)
              if (id.includes("react/") && !id.includes("react-dom")) {
                return "react";
              }
              if (id.includes("react-dom")) {
                return "react-dom";
              }
              if (id.includes("react-router") || id.includes("@react-router")) {
                return "react-router";
              }
              
              // UI libraries (lazy load)
              if (id.includes("@heroui") || id.includes("@radix-ui") || id.includes("@headlessui")) {
                return "ui-libs";
              }
              
              // Heavy editors (lazy load on demand)
              if (id.includes("@monaco-editor") || id.includes("monaco-editor")) {
                return "monaco";
              }
              
              // Terminal (lazy load)
              if (id.includes("xterm") || id.includes("@xterm")) {
                return "xterm";
              }
              
              // Icons (split by library)
              if (id.includes("lucide-react")) {
                return "icons-lucide";
              }
              if (id.includes("react-icons")) {
                return "icons-react";
              }
              
              // Diagrams - skip mermaid chunking entirely due to circular deps
              // Mermaid will be bundled with vendor or loaded dynamically
              // Note: cytoscape/dagre removed - not currently installed
              // if (id.includes("cytoscape") || id.includes("dagre")) {
              //   return "graph-libs";
              // }
              
              // Math/Jupyter (lazy load)
              if (id.includes("katex") || id.includes("jupyter")) {
                return "jupyter";
              }
              
              // State management
              if (id.includes("@reduxjs/toolkit") || id.includes("react-redux")) {
                return "redux";
              }
              if (id.includes("@tanstack/react-query")) {
                return "react-query";
              }
              
              // WebSocket
              if (id.includes("socket.io-client") || id.includes("engine.io")) {
                return "socketio";
              }
              
              // HTTP clients
              if (id.includes("axios")) {
                return "axios";
              }
              
              // i18n
              if (id.includes("i18next") || id.includes("react-i18next")) {
                return "i18n";
              }
              
              // Syntax highlighting (lazy load)
              if (id.includes("react-syntax-highlighter") || id.includes("prism") || id.includes("hljs")) {
                return "syntax-highlighter";
              }
              
              // Markdown (lazy load)
              if (id.includes("react-markdown") || id.includes("remark") || id.includes("rehype")) {
                return "markdown";
              }
              
              // Utilities (smaller)
              if (id.includes("date-fns") || id.includes("clsx") || id.includes("tailwind-merge")) {
                return "utils";
              }
              
              // Everything else in minimal vendor bundle
              return "vendor";
            }
            
            // Route-based code splitting
            if (id.includes("src/routes/home")) return "home";
            if (id.includes("src/routes/conversation.tsx") || id.includes("src/routes/conversation/")) 
              return "conversation";
            if (id.includes("src/routes/settings")) return "settings";
            if (id.includes("src/routes/database-browser")) return "database-browser";
            if (id.includes("src/routes/microagent-management")) return "microagent";
            
            // Component-based splitting
            if (id.includes("src/components/features/chat") && !id.includes("__tests__")) 
              return "chat";
            if (id.includes("src/components/features/orchestration")) 
              return "orchestration";
            if (id.includes("src/components/features/browser")) 
              return "browser";
            if (id.includes("src/components/features/database-browser"))
              return "db-components";
            
            return undefined;
          },
          chunkFileNames: "assets/[name]-[hash].js",
          entryFileNames: "assets/[name]-[hash].js",
          assetFileNames: "assets/[name]-[hash].[ext]",
        },
      },
      chunkSizeWarningLimit: 500, // Stricter limit
    },
    resolve: {
      alias: {
        "#": path.resolve(process.cwd(), "src"),
        "#/": `${path.resolve(process.cwd(), "src")}/`,
        // Force all React imports to resolve to the same module instance
        "react": path.resolve(process.cwd(), "node_modules/react"),
        "react-dom": path.resolve(process.cwd(), "node_modules/react-dom"),
      },
      // Ensure a single instance of React/ReactDOM is used to avoid
      // "Invalid hook call" and context errors when mixed versions load.
      dedupe: ["react", "react-dom", "react-router", "react-router-dom", "react-redux", "@reduxjs/toolkit"],
    },
    plugins: [
      // Disable react-router plugin for pure SPA builds to avoid any SSR/prerender paths
      PURE_SPA ? null : reactRouterPlugin,
      fixManifestPlugin(),
      viteTsconfigPaths(),
      svgr(),
      tailwindcss(),
    ]
      .flat()
      .filter(Boolean),
    optimizeDeps: {
      exclude: ["mermaid"], // Exclude mermaid to avoid circular dependency errors
      include: [
        "react-redux",
        "posthog-js",
        "@tanstack/react-query",
        "react-hot-toast",
        "@reduxjs/toolkit",
        "i18next",
        "i18next-http-backend",
        "i18next-browser-languagedetector",
        "react-i18next",
        "axios",
        "date-fns",
        "@uidotdev/usehooks",
        "react-icons/fa6",
        "react-icons/fa",
        "clsx",
        "tailwind-merge",
        "@heroui/react",
        "lucide-react",
        "@microlink/react-json-view",
        "socket.io-client",
        "react-icons/vsc",
        "react-icons/lu",
        "react-icons/di",
        "react-icons/io5",
        "react-icons/io",
        "@monaco-editor/react",
        "react-textarea-autosize",
        "react-markdown",
        "remark-gfm",
        "remark-breaks",
        "react-syntax-highlighter",
        "react-syntax-highlighter/dist/esm/styles/prism",
        "react-syntax-highlighter/dist/esm/styles/hljs",
        "@xterm/addon-fit",
        "@xterm/xterm",
      ],
    },
    server: {
      port: FE_PORT,
      host: true,
      strictPort: true,
      allowedHosts: true,
      // Explicit HMR settings: ensure the client connects back to localhost
      // over the correct websocket protocol and port. This helps when the
      // dev server is bound to 0.0.0.0 or multiple network interfaces.
      // Use default HMR settings; explicit overrides can cause mismatch
      // when accessed via different hostnames or extensions.
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
      // Fix for React Router v7 SPA mode - ensure static assets are served properly
      fs: {
        strict: false,
      },
      // Add fallback to handle static assets that React Router might intercept
      middlewareMode: false,
      // Configure historyApiFallback to handle SPA routing properly
      historyApiFallback: {
        index: '/index.html',
        // Don't fallback for assets, let Vite handle them
        disableDotRule: true,
      },
    },
    clearScreen: false,
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: "./vitest.setup.ts",
      coverage: {
        provider: "v8",
        reporter: ["text", "json", "html"],
        exclude: [
          "node_modules/",
          "build/",
          "**/*.d.ts",
          "**/*.config.*",
          "**/mockData",
          "**/__tests__/**",
        ],
      },
    },
  };
});
