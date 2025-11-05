import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// This repro intentionally simulates a plugin factory that returns a plugin
// object without a `name` property. The React Router CLI looks for a plugin
// named 'react-router' and will report "React Router Vite plugin not found"
// if it can't find one.

function simulateReactRouterFactory() {
  // Returns a Vite plugin-like object with a required `name` property.
  return {
    name: "simulate-react-router", // Added name property
    configureServer(server: import("vite").ViteDevServer) {
      // noop
    },
  };
}

export default defineConfig({
  plugins: [react(), simulateReactRouterFactory()],
  server: { port: 5173 },
});
