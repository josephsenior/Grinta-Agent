import { useEffect, useCallback } from "react";
import { logger } from "#/utils/logger";

// Hook for performance optimizations
export const usePerformanceOptimization = () => {
  // Preload critical resources
  const preloadCriticalResources = useCallback(() => {
    // No critical images configured. Add paths here if you add assets to /public.
  }, []);

  // Optimize font loading
  const optimizeFontLoading = useCallback(() => {
    // Add font-display: swap to improve font loading
    const style = document.createElement("style");
    style.textContent = `
      @font-face {
        font-family: 'Inter';
        font-display: swap;
      }
    `;
    document.head.appendChild(style);
  }, []);

  // Enable resource hints
  const enableResourceHints = useCallback(() => {
    // Add DNS prefetch for external domains
    const domains = ["fonts.googleapis.com", "fonts.gstatic.com"];

    domains.forEach((domain) => {
      const link = document.createElement("link");
      link.rel = "dns-prefetch";
      link.href = `//${domain}`;
      document.head.appendChild(link);
    });
  }, []);

  // Initialize performance optimizations
  useEffect(() => {
    preloadCriticalResources();
    optimizeFontLoading();
    enableResourceHints();

    // Enable requestIdleCallback for non-critical tasks
    if ("requestIdleCallback" in window) {
      requestIdleCallback(() => {
        // Preload non-critical resources during idle time
        logger.debug("Idle time available for background tasks");
      });
    }
  }, [preloadCriticalResources, optimizeFontLoading, enableResourceHints]);

  return {
    preloadCriticalResources,
    optimizeFontLoading,
    enableResourceHints,
  };
};
