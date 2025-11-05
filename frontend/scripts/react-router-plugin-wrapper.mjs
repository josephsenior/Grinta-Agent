// Thin wrapper that normalizes the value returned by `reactRouter()` into a
// plain plugin or plugin array where at least one plugin has the name
// 'react-router'. This ensures programmatic loaders (like @react-router/dev's
// CLI) can reliably detect the plugin when resolving the Vite config.
import { reactRouter as _reactRouter } from "@react-router/dev/vite";
import config from "../react-router.config.ts";

function normalize(pluginFactory) {
  const p = pluginFactory(config);
  if (Array.isArray(p)) {
    const arr = p.slice();
    const hasNamed = arr.some((pl) => pl && (pl.name === "react-router" || pl.name === "react-router/rsc"));
    if (!hasNamed) {
      arr.unshift({ name: "react-router" });
    }
    return arr;
  }
  if (p && typeof p === "object") {
    const pluginObj = Object.assign({}, p);
    if (!pluginObj.name) {
      pluginObj.name = "react-router";
    }
    // Add configuration to properly handle static assets in SPA mode
    if (pluginObj.configureServer) {
      const originalConfigureServer = pluginObj.configureServer;
      pluginObj.configureServer = function(server) {
        // Add middleware to handle static assets before React Router
        server.middlewares.use((req, res, next) => {
          // Skip React Router for static assets
          if (req.url && (
            req.url.startsWith('/assets/') ||
            req.url.startsWith('/src/') ||
            req.url.includes('.css') ||
            req.url.includes('.js') ||
            req.url.includes('.png') ||
            req.url.includes('.svg') ||
            req.url.includes('.ico') ||
            req.url.includes('.woff') ||
            req.url.includes('.woff2') ||
            req.url.includes('.ttf') ||
            req.url.includes('.eot')
          )) {
            // Let Vite handle static assets
            return next();
          }
          // For all other requests, call the original React Router handler
          return originalConfigureServer.call(this, server, req, res, next);
        });
      };
    }
    return [pluginObj];
  }
  // If nothing sensible returned, expose a no-op plugin with the expected name
  return [{ name: "react-router" }];
}

export default normalize(_reactRouter);
